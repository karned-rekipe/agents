import asyncio

from langchain_core.messages import HumanMessage
from loguru import logger

from agent_config import load_config
from graph import RecipeState, build_graph


async def main() -> None:
    config = load_config()
    graph = build_graph(config)

    logger.info(f"🤖 Recipe creator ready mcp={config.mcp.url} planner={config.lm.planner.model_name}")
    print("\nDécris ta recette en langage naturel. (quit pour quitter)\n")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in ("exit", "quit", "q"):
                break
            if not user_input:
                continue

            initial_state: RecipeState = {
                "messages": [HumanMessage(content = user_input)],
                "plan": None,
                "resolved_ingredients": {},
                "resolved_ustensils": {},
                "recipe_uuid": None,
                "error": None,
            }

            result = await graph.ainvoke(initial_state)
            print("\n" + result["messages"][-1].content + "\n")

        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    asyncio.run(main())
