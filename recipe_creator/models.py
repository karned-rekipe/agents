from pydantic import BaseModel, Field


class IngredientLine(BaseModel):
    name: str = Field(description = "Nom de l'ingrédient (ex. Farine de blé)")
    unit: str | None = Field(default = None, description = "Unité de mesure (g, kg, ml, …). None si non applicable.")


class UstensilLine(BaseModel):
    name: str = Field(description = "Nom de l'ustensil (ex. Fouet, Poêle)")


class RecipePlan(BaseModel):
    name: str = Field(description = "Nom de la recette")
    description: str | None = Field(default = None, description = "Description courte de la recette")
    ingredients: list[IngredientLine] = Field(default_factory = list)
    ustensils: list[UstensilLine] = Field(default_factory = list)
