from abc import abstractmethod
from typing import Any, Dict, List, Optional


class BaseClient:
    @abstractmethod
    def completions(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> str:
        pass
