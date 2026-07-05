from abc import ABC, abstractmethod
from typing import Any


class ModelRunner(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str, config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
