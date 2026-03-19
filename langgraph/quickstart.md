# Quickstart — LangGraph

Agent CLI avec `StateGraph` custom (ReAct manuel), connecté au serveur MCP Rekipe via Streamable HTTP.

## Prérequis

- Python 3.13
- [uv](https://docs.astral.sh/uv/) installé
- Serveur MCP Rekipe en cours d'exécution (`main_mcp_http.py` dans `_sample`)
- Modèle LLM accessible via une API compatible OpenAI (LM Studio, Ollama, OpenAI…)

## Installation

```bash
cd agents/langgraph
uv sync
```

## Configuration

Édite `config.yaml` :

```yaml
mcp:
  url: http://127.0.0.1:8001/mcp   # URL du serveur MCP

lm:
  model_name: qwen/qwen3.5-9b      # identifiant du modèle
  base_url: http://localhost:1234/v1
  api_key: lm-studio
```

## Lancer l'agent

```bash
uv run python main.py
```

Tape ta question au prompt `>`, `q` pour quitter.

## Architecture du graph

```
[START] → agent → tools → agent → … → [END]
                ↘ (pas de tool call) → [END]
```

Le nœud `agent` appelle le LLM avec le system prompt + l'historique.
Le nœud `tools` exécute les tools MCP retournés par le modèle.

