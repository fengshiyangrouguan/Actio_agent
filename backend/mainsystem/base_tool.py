from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolExecutionContext:
    task_id: str
    session_id: str
    user_input: str
    mode: str
    bot_profile: Dict[str, Any] = field(default_factory=dict)
    memory_window: List[Dict[str, str]] = field(default_factory=list)


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    def scopes(self) -> List[str]:
        return ["main"]

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    @abstractmethod
    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Any:
        raise NotImplementedError
