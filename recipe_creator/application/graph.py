from adapters.fuzzy import make_fuzzy_matcher
from adapters.mcp_repository import MCPRecipeRepository
from adapters.planner import PydanticAIPlanner
from application.nodes.create_recipe import make_create_recipe_node
from application.nodes.plan import make_plan_node
from application.nodes.resolve_ingredients import make_resolve_ingredients_node
from application.nodes.resolve_ustensils import make_resolve_ustensils_node
from application.state import RecipeState
from infrastructure.config import AgentConfig
from langgraph.graph import END, StateGraph


def build_graph(config: AgentConfig):
    planner = PydanticAIPlanner(config.lm.planner)
    repository = MCPRecipeRepository(config.mcp.url)
    matcher = make_fuzzy_matcher(config.fuzzy.threshold)

    g = StateGraph(RecipeState)
    g.add_node("plan", make_plan_node(planner))
    g.add_node("resolve_ingredients", make_resolve_ingredients_node(repository, matcher))
    g.add_node("resolve_ustensils", make_resolve_ustensils_node(repository, matcher))
    g.add_node("create_recipe", make_create_recipe_node(repository))

    g.set_entry_point("plan")
    g.add_edge("plan", "resolve_ingredients")
    g.add_edge("resolve_ingredients", "resolve_ustensils")
    g.add_edge("resolve_ustensils", "create_recipe")
    g.add_edge("create_recipe", END)

    return g.compile()
