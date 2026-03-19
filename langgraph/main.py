import asyncio

from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from loguru import logger

from agent_config import load_config

_SYSTEM_PROMPT = (
    "Tu es un assistant culinaire pour l'application Rekipe. "
    "Tu gères les ingrédients en base de données via les tools disponibles. "
    "Réponds toujours en français, de façon concise et utile."
)


def _build_graph(model: ChatOpenAI, tools: list):
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    def call_model(state: MessagesState):
        messages = [SystemMessage(content = _SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [model_with_tools.invoke(messages)]}

    def should_continue(state: MessagesState):
        if state["messages"][-1].tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


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
        graph = _build_graph(model, tools)

        logger.info(f"🤖 LangGraph agent ready mcp={config.mcp.url} model={config.lm.model_name}")

        history = []
        while True:
            try:
                user_input = input("\n> ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    break
                if not user_input:
                    continue

                result = await graph.ainvoke({"messages": history + [{"role": "user", "content": user_input}]})
                history = result["messages"]
                print(result["messages"][-1].content)
            except (KeyboardInterrupt, EOFError):
                break


if __name__ == "__main__":
    asyncio.run(main())
