import chainlit as cl
from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from agent_config import load_config

_config = load_config()
logger.info(f"🤖 Agent starting mcp={_config.mcp.url} model={_config.lm.model_name}")

_mcp_server = MCPServerStreamableHTTP(_config.mcp.url)

_model = OpenAIChatModel(
    _config.lm.model_name,
    provider = OpenAIProvider(
        base_url = _config.lm.base_url,
        api_key = _config.lm.api_key,
    ),
)

_agent = Agent(
    _model,
    toolsets = [_mcp_server],
    system_prompt = (
        "Tu es un assistant culinaire pour l'application Rekipe. "
        "Tu gères les ingrédients en base de données via les tools disponibles. "
        "Réponds toujours en français, de façon concise et utile."
    ),
)


def _log_tool_calls(all_messages: list, history_count: int) -> None:
    for msg in all_messages[history_count:]:
        if not hasattr(msg, "parts"):
            continue
        for part in msg.parts:
            kind = type(part).__name__
            if kind == "ToolCallPart":
                logger.info(f"🔧 Tool called tool={part.tool_name} args={part.args}")
            elif kind == "ToolReturnPart":
                logger.info(f"↩️ Tool returned tool={part.tool_name} content={str(part.content)[:200]}")


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("history", [])
    logger.info("🚀 New chat session started")


@cl.on_message
async def on_message(message: cl.Message) -> None:
    history = cl.user_session.get("history", [])
    logger.info(f"📨 Message received content={message.content[:120]}")
    response = cl.Message(content = "")
    await response.send()

    try:
        async with _agent:
            async with _agent.run_stream(str(message.content), message_history = history) as result:
                async for chunk in result.stream_text(delta = True):
                    await response.stream_token(chunk)
                new_history = result.all_messages()

        _log_tool_calls(new_history, len(history))
        cl.user_session.set("history", new_history)
    except Exception as e:
        logger.error(f"Agent error error={e}")
        response.content = f"⚠️ Erreur : {e}"

    await response.update()
