from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIModelProfile
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider
from loguru import logger

from agent_config import LMSettings
from models import RecipePlan

_SYSTEM_PROMPT = (
    "Tu es un assistant d'extraction culinaire. "
    "À partir d'une description en langage naturel, tu structures une recette complète. "
    "Identifie tous les ingrédients avec leur unité si mentionnée. "
    "Identifie tous les ustensiles nécessaires. "
    "Décompose la recette en étapes ordonnées avec leur durée estimée si possible. "
    "Dans chaque étape, référence uniquement des noms d'ingrédients et d'ustensiles "
    "qui apparaissent dans les listes ingredients et utensils. "
    "Déduis un nom de recette si non explicitement donné. "
    "Réponds toujours en français."
)

# Used only for OpenAI-compatible local models.
# 'prompted' avoids tool-calling (unreliable on local LLMs like Qwen3/LLaMA).
# openai_chat_send_back_thinking_parts=False prevents thinking tokens from
# accumulating in retry context and blowing the context window.
_OPENAI_PROFILE = OpenAIModelProfile(
    default_structured_output_mode = "prompted",
    openai_chat_send_back_thinking_parts = False,
)


def build_planner(settings: LMSettings) -> Agent:
    if settings.provider == "anthropic":
        logger.debug(f"build_planner provider=anthropic model={settings.model_name} retries=3")
        model = AnthropicModel(
            settings.model_name,
            provider = AnthropicProvider(api_key = settings.api_key),
        )
    else:
        if not settings.base_url:
            raise ValueError("base_url is required for provider='openai'")
        logger.debug(
            f"build_planner provider=openai model={settings.model_name} "
            f"base_url={settings.base_url} structured_output_mode=prompted retries=3"
        )
        model = OpenAIChatModel(
            settings.model_name,
            provider = OpenAIProvider(base_url = settings.base_url, api_key = settings.api_key),
            profile = _OPENAI_PROFILE,
        )

    return Agent(model, output_type = RecipePlan, system_prompt = _SYSTEM_PROMPT, retries = 3)
