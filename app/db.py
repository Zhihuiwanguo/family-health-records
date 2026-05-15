from __future__ import annotations

from typing import Any

from postgrest.exceptions import APIError

from app.supabase_client import get_supabase


class DBFetchError(Exception):
    def __init__(self, table: str, message: str):
        super().__init__(message)
        self.table = table
        self.message = message


def _is_missing_created_at_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "created_at" in text and (
        "does not exist" in text or "column" in text or "not found" in text
    )


def _friendly_error_message(table: str, exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "does not exist" in lower and "relation" in lower:
        return f"数据表 {table} 不存在，请先初始化数据库。"
    if "permission denied" in lower or "not allowed" in lower or "forbidden" in lower:
        return f"没有访问数据表 {table} 的权限，请检查 Supabase key 和 RLS 策略。"
    return f"读取数据表 {table} 失败：{text}"


def fetch_with_status(table: str, **eq_filters):
    try:
        q = get_supabase().table(table).select("*")
        for k, v in eq_filters.items():
            if v is not None:
                q = q.eq(k, v)
        try:
            result = q.order("created_at", desc=True).execute()
        except Exception as exc:
            if not _is_missing_created_at_error(exc):
                raise
            result = q.execute()
        return result.data or [], None
    except (APIError, RuntimeError, Exception) as exc:
        return [], DBFetchError(table=table, message=_friendly_error_message(table, exc))


def fetch(table: str, **eq_filters):
    data, _ = fetch_with_status(table, **eq_filters)
    return data


def insert(table: str, payload: dict[str, Any]):
    return get_supabase().table(table).insert(payload).execute()


def upsert(table: str, payload: dict[str, Any], on_conflict: str | None = None):
    return get_supabase().table(table).upsert(payload, on_conflict=on_conflict).execute()


def update(table: str, row_id: str, payload: dict[str, Any]):
    return get_supabase().table(table).update(payload).eq("id", row_id).execute()
