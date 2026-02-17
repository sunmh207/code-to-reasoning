"""Token 计数与截断（兼容无 tiktoken 环境）"""


def count_tokens(text: str) -> int:
    """粗略估算 token 数量（约 4 字符/token）"""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        return len(text) // 4


def truncate_text_by_tokens(text: str, max_tokens: int) -> str:
    """按 token 数量截断"""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) > max_tokens:
            return encoding.decode(tokens[:max_tokens])
        return text
    except ImportError:
        return text[: max_tokens * 4] if len(text) > max_tokens * 4 else text
