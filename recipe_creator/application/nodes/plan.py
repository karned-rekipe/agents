from collections.abc import Callable

import time
from application.state import RecipeState
from domain.ports import PlannerPort
from loguru import logger


def make_plan_node(planner: PlannerPort) -> Callable:
    async def plan_node(state: RecipeState) -> dict:
        user_message = state["messages"][-1].content
        logger.info(f"▶ [plan] length={len(user_message)} content={user_message[:200]!r}")
        t0 = time.perf_counter()

        plan = await planner.plan(user_message)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"◀ [plan] {elapsed_ms:.0f}ms — "
            f"name={plan.name!r} "
            f"ingredients={len(plan.ingredients)} "
            f"ustensils={len(plan.ustensils)}"
        )
        return {"plan": plan}

    return plan_node
