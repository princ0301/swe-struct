from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator

class ArmConfig(BaseModel):
    id: str
    name: str
    tools: list[str]
    reminder: bool = False
    force_first_tool: str | None = None
    passive_hints: bool = False
    shuffle_graph: bool = False
    graph_tool_description: str | None = None

    @model_validator(mode="after")
    def check_forced_tool_is_available(self) -> "ArmConfig":
        if self.force_first_tool and self.force_first_tool not in self.tools:
            raise ValueError(f"forced tool not in tools: {self.force_first_tool}")
        return self

def load_arms(path: Path) -> dict[str, ArmConfig]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {arm_id: ArmConfig(id=arm_id, **fields) for arm_id, fields in raw["arms"].items()}