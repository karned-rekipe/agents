from collections.abc import Callable

import time
from application.state import RecipeState
from domain.models import RecipePlan
from domain.ports import RecipeRepositoryPort
from loguru import logger


def _format_response(plan: RecipePlan, uuid: str, resolved_ingredients: dict, resolved_ustensils: dict) -> str:
    lines: list[str] = []

    # Header
    lines.append(f"✅ **{plan.name}** créée avec succès — 🆔 `{uuid}`")

    if plan.description:
        lines.append(f"\n_{plan.description}_")

    # Meta
    meta: list[str] = []
    if plan.servings:
        meta.append(f"👥 {plan.servings}")
    if plan.prep_time_minutes:
        meta.append(f"⏱ Prépa : {plan.prep_time_minutes} min")
    if plan.cook_time_minutes:
        meta.append(f"🔥 Cuisson : {plan.cook_time_minutes} min")
    if meta:
        lines.append("  •  ".join(meta))

    # Ingredients
    if plan.ingredients:
        lines.append("\n## 🥕 Ingrédients")
        for ing in plan.ingredients:
            parts = []
            if ing.quantity:
                parts.append(ing.quantity)
            if ing.unit:
                parts.append(ing.unit)
            prefix = " ".join(parts)
            lines.append(f"- {'**' + prefix + '**  ' if prefix else ''}{ing.name}")

    # Ustensils
    if plan.ustensils:
        lines.append("\n## 🍳 Ustensiles")
        for ust in plan.ustensils:
            lines.append(f"- {ust.name}")

    # Steps
    if plan.steps:
        lines.append("\n## 📋 Étapes")
        for i, step in enumerate(plan.steps, 1):
            duration = f" _{step.duration_minutes} min_" if step.duration_minutes else ""
            lines.append(f"\n**{i}. {step.title}**{duration}")
            lines.append(step.instruction)

    return "\n".join(lines)


def make_create_recipe_node(repository: RecipeRepositoryPort) -> Callable:
    async def create_recipe_node(state: RecipeState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [create_recipe] name={plan.name!r}")
        t0 = time.perf_counter()

        created = await repository.create_recipe(plan.name, plan.description)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_recipe] 🎉 uuid={created['uuid']} in {elapsed_ms:.0f}ms")

        content = _format_response(plan, created["uuid"], state["resolved_ingredients"], state["resolved_ustensils"])
        return {
            "recipe_uuid": created["uuid"],
            "messages": [{"role": "assistant", "content": content}],
        }

    return create_recipe_node
