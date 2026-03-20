from abc import ABC, abstractmethod
from collections.abc import Callable

from domain.models import RecipePlan


class PlannerPort(ABC):
    @abstractmethod
    async def plan(self, user_input: str) -> RecipePlan: ...


class RecipeRepositoryPort(ABC):
    @abstractmethod
    async def list_ingredients(self, name: str) -> list[dict]: ...

    @abstractmethod
    async def create_ingredient(self, name: str, unit: str | None) -> dict: ...

    @abstractmethod
    async def list_ustensils(self, name: str) -> list[dict]: ...

    @abstractmethod
    async def create_ustensil(self, name: str) -> dict: ...

    @abstractmethod
    async def create_recipe(self, name: str, description: str | None) -> dict: ...


# Matcher: (name, candidates) → matched candidate or None
NameMatcher = Callable[[str, list[dict]], dict | None]
