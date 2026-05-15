from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def parse_date(v: str | None):
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def safe_json_loads(text: str) -> dict[str, Any]:
    import json
    try:
        return json.loads(text)
    except Exception:
        return {"warnings": ["JSON 解析失败"], "raw": text}


def mask_identifier(text: str) -> str:
    patterns = [
        r"(\b1\d{10}\b)",
        r"(\b\d{17}[\dXx]\b)",
        r"(门诊号[:：]?\s*[A-Za-z0-9-]+)",
        r"(住院号[:：]?\s*[A-Za-z0-9-]+)",
        r"(检查号[:：]?\s*[A-Za-z0-9-]+)",
        r"(影像号[:：]?\s*[A-Za-z0-9-]+)",
    ]
    masked = text
    for p in patterns:
        masked = re.sub(p, "[已脱敏]", masked)
    masked = re.sub(r"姓名[:：]?\s*\S+", "姓名: [已脱敏]", masked)
    return masked
