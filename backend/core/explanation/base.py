from abc import ABC, abstractmethod
from typing import Dict, Any

class ExplanationProvider(ABC):
    @abstractmethod
    def explain(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass
