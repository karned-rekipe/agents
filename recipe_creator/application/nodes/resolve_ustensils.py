from collections.abc import Callable

import time
from application.state import RecipeState
from domain.ports import NameMatcher, RecipeRepositoryPort
from loguru import logger


def make_resolve_ustensils_node(repository: RecipeRepositoryPort, matcher: NameMatcher) -> Callable:
    async def resolve_ustensils_node(state: RecipeState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [resolve_ustensils] {len(plan.ustensils)} ustensil(s)")
        t0 = time.perf_counter()
        resolved: dict[str, str] = {}

        for line in plan.ustensils:
            candidates = await repository.list_ustensils(line.name)
            match = matcher(line.name, candidates)
            if match:
                logger.info(f"  ♻️  reuse ustensil name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created = await repository.create_ustensil(line.name)
                logger.info(f"  ✅ create ustensil name={line.name!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ustensils] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ustensils": resolved}

    return resolve_ustensils_node
