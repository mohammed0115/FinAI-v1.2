from abc import ABC, abstractmethod

class AIPlugin(ABC):
    code: str
    name: str

    @abstractmethod
    def execute(self, payload: dict) -> dict:
        pass
