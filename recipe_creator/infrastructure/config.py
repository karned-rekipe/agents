from pathlib import Path

import yaml
from pydantic import BaseModel

_DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"


class MCPSettings(BaseModel):
    url: str


class LMSettings(BaseModel):
    model_name: str
    provider: str = "openai"  # "openai" | "anthropic"
    base_url: str | None = None
    api_key: str = "local"


class LMConfig(BaseModel):
    planner: LMSettings
    executor: LMSettings


class FuzzySettings(BaseModel):
    threshold: int = 80


class AgentConfig(BaseModel):
    mcp: MCPSettings
    lm: LMConfig
    fuzzy: FuzzySettings = FuzzySettings()


def load_config(config_path: Path | None = None) -> AgentConfig:
    path = config_path or _DEFAULT_CONFIG
    with path.open() as f:
        data = yaml.safe_load(f)
    return AgentConfig.model_validate(data)
