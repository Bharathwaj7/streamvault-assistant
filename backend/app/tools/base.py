from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """All tools must implement name, description, parameters_schema, and run."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters_schema(self) -> dict: ...

    @abstractmethod
    async def run(self, **kwargs) -> Any: ...

    def to_groq_schema(self) -> dict:
        """Convert tool to Groq/OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters":  self.parameters_schema,
            },
        }
