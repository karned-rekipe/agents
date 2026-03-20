# Rekipe — Recipe Creator Agent

Agent multi-couche de création de recettes depuis le langage naturel.

**Stack :** LangGraph (orchestration) · PydanticAI (extraction structurée) · FastMCP (données)

## Prérequis

- Python 3.13
- `uv` installé
- Serveur MCP Rekipe démarré (voir `_sample`)
- Clé API OpenAI (ou modèle local compatible structured output)

## Installation

```bash
uv sync
```

## Configuration

Éditer `config.yaml` :

| Clé                      | Description                                              |
|--------------------------|----------------------------------------------------------|
| `mcp.url`                | URL du serveur MCP Rekipe                                |
| `lm.planner.model_name`  | Modèle pour l'extraction structurée (ex. `gpt-4o-mini`)  |
| `lm.planner.api_key`     | Clé API OpenAI                                           |
| `lm.executor.model_name` | Modèle local pour l'orchestration (ex. `ministral-3:8b`) |
| `fuzzy.threshold`        | Seuil de déduplication 0–100 (défaut : 80)               |

> **Note :** Le Planner doit utiliser un modèle supportant le **structured output** (OpenAI `gpt-4o-mini` recommandé).
> Les modèles Ollama/LM Studio ne le garantissent pas tous.

## Lancement

### Interface web (Chainlit)

```bash

chainlit run main.py
```

Ouvrir http://localhost:8000 dans le navigateur.

### Terminal

```bash
python cli.py
```

## Flow

```
[Message utilisateur]
        ↓
   [Planner — PydanticAI]       extraction → RecipePlan structuré
        ↓
   [resolve_ingredients]        list MCP → fuzzy match → create si absent
        ↓
   [resolve_utensils]           list MCP → fuzzy match → create si absent
        ↓
   [create_etapes]              create MCP pour chaque étape avec UUIDs résolus
        ↓
   [create_recipe]              create MCP recette finale
        ↓
   [Réponse utilisateur]        résumé avec UUID
```

## Exemple d'input

> "Je veux faire une quiche lorraine. Il me faut des œufs, de la crème fraîche, des lardons et une pâte brisée. Comme
> ustensiles un moule à tarte et un fouet. D'abord on étale la pâte (5 min), ensuite on mélange les œufs et la crème (3
> min), on ajoute les lardons et on enfourne 30 min à 180°C."

