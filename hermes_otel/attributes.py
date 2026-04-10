"""Attribute truncation utilities for OpenTelemetry span attributes."""

import json
from typing import Any, Optional

DEFAULT_MAX_LEN = 8000


def json_attr(value: Any, max_len: int = DEFAULT_MAX_LEN) -> str:
    """Serialize value to JSON string, truncating if needed."""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)

    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    return text


def text_attr(text: Optional[str], max_len: int = DEFAULT_MAX_LEN) -> Optional[str]:
    """Truncate text string to max length."""
    if text is None:
        return None
    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    return text
