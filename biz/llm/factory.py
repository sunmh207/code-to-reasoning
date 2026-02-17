import os

from biz.llm.client.base import BaseClient
from biz.llm.client.deepseek import DeepSeekClient
from biz.utils.log import logger


class Factory:
    @staticmethod
    def get_client(provider: str = None) -> BaseClient:
        provider = (provider or os.getenv("LLM_PROVIDER", "deepseek")).lower()
        if provider == "deepseek":
            return DeepSeekClient()
        raise ValueError(f"Unknown LLM provider: {provider}")
