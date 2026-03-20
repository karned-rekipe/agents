from collections.abc import Callable

import time
from application.state import RecipeState
from domain.ports import NameMatcher, RecipeRepositoryPort
from loguru import logger


def make_resolve_ingredients_node(repository: RecipeRepositoryPort, matcher: NameMatcher) -> Callable:
    async def resolve_ingredients_node(state: RecipeState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [resolve_ingredients] {len(plan.ingredients)} ingredient(s)")
        t0 = time.perf_counter()
        resolved: dict[str, str] = {}

        for line in plan.ingredients:
            candidates = await repository.list_ingredients(line.name)
            match = matcher(line.name, candidates)
            if match:
                logger.info(f"  ♻️  reuse ingredient name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created = await repository.create_ingredient(line.name, line.unit)
                logger.info(f"  ✅ create ingredient name={line.name!r} unit={line.unit!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ingredients] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ingredients": resolved}

    return resolve_ingredients_node
