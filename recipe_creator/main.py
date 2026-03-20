import chainlit as cl
from langchain_core.messages import HumanMessage
from loguru import logger

from application.graph import build_graph
from application.state import RecipeState
from infrastructure.config import load_config
from infrastructure.logging import setup_logging

setup_logging()

_config = load_config()
_graph = build_graph(_config)

logger.info(
    f"🤖 Recipe creator agent ready "
    f"mcp={_config.mcp.url} "
    f"planner={_config.lm.planner.model_name} "
    f"fuzzy_threshold={_config.fuzzy.threshold}"
)


@cl.on_chat_start
async def on_chat_start() -> None:
    logger.info("🚀 New chat session started")


@cl.on_message
async def on_message(message: cl.Message) -> None:
    logger.info(f"📨 Message received length={len(message.content)} content={message.content[:200]!r}")
    response = cl.Message(content = "")
    await response.send()

    initial_state: RecipeState = {
        "messages": [HumanMessage(content = message.content)],
        "plan": None,
        "resolved_ingredients": {},
        "resolved_ustensils": {},
        "recipe_uuid": None,
        "error": None,
    }

    try:
        result = await _graph.ainvoke(initial_state)
        logger.info(
            f"✅ Graph completed "
            f"recipe_uuid={result.get('recipe_uuid')} "
            f"ingredients={len(result.get('resolved_ingredients', {}))} "
            f"ustensils={len(result.get('resolved_ustensils', {}))}"
        )
        last = result["messages"][-1]
        response.content = last.content if hasattr(last, "content") else str(last)
    except Exception as e:
        logger.exception(f"💥 Agent error: {e}")
        response.content = f"⚠️ Erreur : {e}"

    await response.update()
