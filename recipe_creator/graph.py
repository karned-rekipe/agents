import json
import time
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from rapidfuzz import fuzz, process

from agent_config import AgentConfig
from models import RecipePlan
from planner import build_planner


class RecipeState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    plan: RecipePlan | None
    resolved_ingredients: dict[str, str]  # name → uuid
    resolved_ustensils: dict[str, str]  # name → uuid
    recipe_uuid: str | None
    error: str | None


def _fuzzy_match(name: str, candidates: list[dict], threshold: int) -> dict | None:
    if not candidates:
        logger.debug(f"  fuzzy_match name={name!r} candidates=[] → no match")
        return None
    names = [c["name"] for c in candidates]
    result = process.extractOne(name, names, scorer = fuzz.WRatio)
    if result and result[1] >= threshold:
        matched = next(c for c in candidates if c["name"] == result[0])
        logger.debug(
            f"  fuzzy_match name={name!r} best={result[0]!r} score={result[1]} threshold={threshold} → MATCH uuid={matched['uuid']}")
        return matched
    best_score = result[1] if result else 0
    best_name = result[0] if result else "—"
    logger.debug(f"  fuzzy_match name={name!r} best={best_name!r} score={best_score} threshold={threshold} → no match")
    return None


async def _call_tool(tools: list, name: str, args: dict) -> Any:
    tool = next((t for t in tools if t.name == name), None)
    if tool is None:
        available = [t.name for t in tools]
        raise ValueError(f"MCP tool not found: '{name}' — outils disponibles: {available}")
    logger.debug(f"  → MCP {name}({json.dumps(args, ensure_ascii = False)})")
    t0 = time.perf_counter()
    result = await tool.ainvoke(args)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if not result:
        logger.debug(f"  ← MCP {name} [] ({elapsed_ms:.0f}ms)")
        return []
    if isinstance(result, list) and isinstance(result[0], dict) and result[0].get("type") == "text":
        parsed = json.loads(result[0]["text"])
        logger.debug(f"  ← MCP {name} {json.dumps(parsed, ensure_ascii = False)[:200]} ({elapsed_ms:.0f}ms)")
        return parsed
    logger.debug(f"  ← MCP {name} {repr(result)[:200]} ({elapsed_ms:.0f}ms)")
    return result


def build_graph(config: AgentConfig):
    planner = build_planner(config.lm.planner)
    mcp_client = MultiServerMCPClient(
        {"rekipe": {"url": config.mcp.url, "transport": "streamable_http"}}
    )

    async def plan_node(state: RecipeState) -> dict:
        user_message = state["messages"][-1].content
        logger.info(f"▶ [plan] input length={len(user_message)} content={user_message[:200]!r}")
        t0 = time.perf_counter()
        try:
            result = await planner.run(user_message)
        except Exception as exc:
            logger.exception(f"💥 [plan] LLM error after {(time.perf_counter() - t0) * 1000:.0f}ms: {exc}")
            raise
        elapsed_ms = (time.perf_counter() - t0) * 1000

        for msg in result.all_messages():
            for part in getattr(msg, "parts", []):
                kind = type(part).__name__
                if kind == "ThinkingPart":
                    logger.debug(f"  LLM thinking ({len(part.content)} chars): {part.content[:300]!r}")
                elif kind == "TextPart":
                    logger.debug(f"  LLM text: {part.content[:500]!r}")
                elif kind == "ToolCallPart":
                    logger.debug(f"  LLM tool_call name={part.tool_name} args={str(part.args)[:300]}")
                elif kind == "ToolReturnPart":
                    logger.debug(f"  LLM tool_return name={part.tool_name} content={str(part.content)[:200]}")
                elif kind == "RetryPromptPart":
                    logger.warning(f"  LLM retry_prompt: {part.content!r}")
                elif kind == "SystemPromptPart":
                    logger.debug(f"  LLM system_prompt ({len(part.content)} chars)")
                elif kind == "UserPromptPart":
                    logger.debug(f"  LLM user_prompt: {str(part.content)[:200]!r}")

        plan: RecipePlan = result.output
        usage = result.usage()
        logger.debug(
            f"  LLM usage requests={usage.requests} "
            f"input_tokens={usage.request_tokens} "
            f"output_tokens={usage.response_tokens} "
            f"total_tokens={usage.total_tokens}"
        )
        logger.info(
            f"◀ [plan] done in {elapsed_ms:.0f}ms — "
            f"name={plan.name!r} "
            f"description={plan.description!r} "
            f"ingredients={len(plan.ingredients)} "
            f"ustensils={len(plan.ustensils)}"
        )
        for i in plan.ingredients:
            logger.debug(f"  ingredient name={i.name!r} unit={i.unit!r}")
        for u in plan.ustensils:
            logger.debug(f"  ustensil  name={u.name!r}")
        return {"plan": plan}

    async def resolve_ingredients_node(state: RecipeState) -> dict:
        plan: RecipePlan = state["plan"]
        logger.info(f"▶ [resolve_ingredients] {len(plan.ingredients)} ingredient(s) to resolve")
        t0 = time.perf_counter()
        tools = await mcp_client.get_tools()
        resolved: dict[str, str] = {}

        for line in plan.ingredients:
            logger.debug(f"  resolving ingredient name={line.name!r} unit={line.unit!r}")
            existing: list[dict] = await _call_tool(tools, "list_ingredients", {"name": line.name})
            logger.debug(f"  list_ingredients returned {len(existing)} candidate(s)")
            match = _fuzzy_match(line.name, existing, config.fuzzy.threshold)
            if match:
                logger.info(f"  ♻️  reuse ingredient name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created: dict = await _call_tool(tools, "create_ingredient", {"name": line.name, "unit": line.unit})
                logger.info(f"  ✅ create ingredient name={line.name!r} unit={line.unit!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ingredients] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ingredients": resolved}

    async def resolve_ustensils_node(state: RecipeState) -> dict:
        plan: RecipePlan = state["plan"]
        logger.info(f"▶ [resolve_ustensils] {len(plan.ustensils)} ustensil(s) to resolve")
        t0 = time.perf_counter()
        tools = await mcp_client.get_tools()
        resolved: dict[str, str] = {}

        for line in plan.ustensils:
            logger.debug(f"  resolving ustensil name={line.name!r}")
            existing: list[dict] = await _call_tool(tools, "list_ustensils", {"name": line.name})
            logger.debug(f"  list_ustensils returned {len(existing)} candidate(s)")
            match = _fuzzy_match(line.name, existing, config.fuzzy.threshold)
            if match:
                logger.info(f"  ♻️  reuse ustensil name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created: dict = await _call_tool(tools, "create_ustensil", {"name": line.name})
                logger.info(f"  ✅ create ustensil name={line.name!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ustensils] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ustensils": resolved}

    async def create_recipe_node(state: RecipeState) -> dict:
        plan: RecipePlan = state["plan"]
        logger.info(f"▶ [create_recipe] name={plan.name!r}")
        payload = {"name": plan.name, "description": plan.description}
        logger.debug(f"  create_recipe payload={json.dumps(payload, ensure_ascii = False)}")
        t0 = time.perf_counter()
        tools = await mcp_client.get_tools()
        created: dict = await _call_tool(tools, "create_recipe", payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_recipe] 🎉 uuid={created['uuid']} in {elapsed_ms:.0f}ms")

        summary = (
            f"✅ Recette **{plan.name}** créée avec succès.\n\n"
            f"- 🥕 {len(state['resolved_ingredients'])} ingrédient(s)\n"
            f"- 🍳 {len(state['resolved_ustensils'])} ustensil(s)\n"
            f"- 🆔 `{created['uuid']}`"
        )
        return {
            "recipe_uuid": created["uuid"],
            "messages": [{"role": "assistant", "content": summary}],
        }

    g = StateGraph(RecipeState)
    g.add_node("plan", plan_node)
    g.add_node("resolve_ingredients", resolve_ingredients_node)
    g.add_node("resolve_ustensils", resolve_ustensils_node)
    g.add_node("create_recipe", create_recipe_node)

    g.set_entry_point("plan")
    g.add_edge("plan", "resolve_ingredients")
    g.add_edge("resolve_ingredients", "resolve_ustensils")
    g.add_edge("resolve_ustensils", "create_recipe")
    g.add_edge("create_recipe", END)

    return g.compile()
