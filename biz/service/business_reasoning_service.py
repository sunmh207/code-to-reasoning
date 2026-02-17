"""
业务推理服务：根据代码 diff 调用 LLM 反推业务变更，返回结构化 JSON
"""
import json
import os
import re
from typing import Any, Dict, List

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BusinessReasoningService:
    def __init__(self):
        self.client = Factory.get_client()
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "conf", "prompt_templates.yml")
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f).get("business_reasoning_prompt", {})
        return {
            "system_message": {"role": "system", "content": cfg.get("system_prompt", "")},
            "user_message": {"role": "user", "content": cfg.get("user_prompt", "")},
        }

    def reason(self, diffs_text: str, commits_text: str) -> Dict[str, Any]:
        """
        调用 LLM 反推业务，返回解析后的 JSON；解析失败时返回含 raw 的默认结构
        """
        if not diffs_text or not diffs_text.strip():
            return self._fallback_result("无有效代码变更")

        max_tokens = int(os.getenv("REASONING_MAX_TOKENS", "10000"))
        if count_tokens(diffs_text) > max_tokens:
            diffs_text = truncate_text_by_tokens(diffs_text, max_tokens)

        user_content = self.prompts["user_message"]["content"].format(
            diffs_text=diffs_text, commits_text=commits_text or "无"
        )
        messages = [
            self.prompts["system_message"],
            {"role": "user", "content": user_content},
        ]
        try:
            raw = self.client.completions(messages)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_result(f"LLM 调用失败: {e}", raw="")

        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON，兼容 markdown 代码块"""
        raw = (raw or "").strip()
        # 去除 ```json ... ``` 包裹
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if m:
            raw = m.group(1).strip()
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return self._fallback_result("返回格式异常", raw=raw)
            summary = data.get("summary", "")
            categories = data.get("categories", [])
            details = data.get("details", [])
            if isinstance(categories, list):
                categories = ",".join(str(c) for c in categories)
            if isinstance(details, list):
                details = json.dumps(details, ensure_ascii=False)
            return {
                "summary": summary or "无法解析",
                "categories": categories,
                "details": details,
                "raw": raw,
            }
        except json.JSONDecodeError as e:
            logger.warn(f"JSON parse failed: {e}, raw={raw[:200]}...")
            return self._fallback_result(f"JSON 解析失败: {e}", raw=raw)

    def _fallback_result(self, msg: str, raw: str = "") -> Dict[str, Any]:
        return {
            "summary": msg,
            "categories": "其他",
            "details": "[]",
            "raw": raw,
        }
