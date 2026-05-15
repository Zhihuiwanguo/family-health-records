from __future__ import annotations

from typing import Any
from app.supabase_client import get_supabase


def fetch(table: str, **eq_filters):
    q = get_supabase().table(table).select("*")
    for k, v in eq_filters.items():
        if v is not None:
            q = q.eq(k, v)
    return q.order("created_at", desc=True).execute().data


def insert(table: str, payload: dict[str, Any]):
    return get_supabase().table(table).insert(payload).execute()


def upsert(table: str, payload: dict[str, Any], on_conflict: str | None = None):
    return get_supabase().table(table).upsert(payload, on_conflict=on_conflict).execute()


def update(table: str, row_id: str, payload: dict[str, Any]):
    return get_supabase().table(table).update(payload).eq("id", row_id).execute()
