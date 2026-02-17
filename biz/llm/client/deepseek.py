import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.utils.log import logger


class DeepSeekClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = os.getenv("DEEPSEEK_API_MODEL", "deepseek-chat")

    def completions(
        self, messages: List[Dict[str, Any]], model: Optional[str] = None
    ) -> str:
        try:
            m = model or self.default_model
            completion = self.client.chat.completions.create(model=m, messages=messages)
            if not completion or not completion.choices:
                return "AI服务返回为空"
            return completion.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
