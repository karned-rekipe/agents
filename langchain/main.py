import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from loguru import logger

from agent_config import load_config

_SYSTEM_PROMPT = (
    "Tu es un assistant culinaire pour l'application Rekipe. "
    "Tu gères les ingrédients en base de données via les tools disponibles. "
    "Réponds toujours en français, de façon concise et utile."
)


async def main() -> None:
    config = load_config()

    model = ChatOpenAI(
        model = config.lm.model_name,
        base_url = config.lm.base_url,
        api_key = config.lm.api_key,
    )

    async with MultiServerMCPClient(
            {"rekipe": {"url": config.mcp.url, "transport": "streamable_http"}}
    ) as client:
        tools = client.get_tools()
        agent = create_react_agent(model, tools, prompt = _SYSTEM_PROMPT)

        logger.info(f"🤖 LangChain agent ready mcp={config.mcp.url} model={config.lm.model_name}")

        while True:
            try:
                user_input = input("\n> ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                if not user_input:
                    continue

                result = await agent.ainvoke({"messages": [{"role": "user", "content": user_input}]})
                print(result["messages"][-1].content)
            except (KeyboardInterrupt, EOFError):
                break


if __name__ == "__main__":
    asyncio.run(main())
