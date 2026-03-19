from pathlib import Path

import yaml
from pydantic import BaseModel


class MCPSettings(BaseModel):
    url: str


class LMSettings(BaseModel):
    model_name: str
    base_url: str
    api_key: str = "local"


class AgentConfig(BaseModel):
    mcp: MCPSettings
    lm: LMSettings


def load_config(config_path: Path | None = None) -> AgentConfig:
    path = config_path or Path(__file__).parent / "config.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return AgentConfig.model_validate(data)
