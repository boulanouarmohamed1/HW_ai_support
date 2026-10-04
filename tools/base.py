from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass(frozen=True)
class ToolSpec:
	name: str
	description: str
	parameters: dict[str, Any]
	handler: Callable[..., dict[str, Any]]
	human_label: dict[str, str] = field(default_factory=dict)
	read_only: bool = True
	max_rows: int = 20
	def schema(self):
		return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}
