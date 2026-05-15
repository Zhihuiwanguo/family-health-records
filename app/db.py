from __future__ import annotations

from typing import Any

import streamlit as st
from postgrest.exceptions import APIError
from supabase import Client, create_client


DB_ERROR_KEY = "db_last_error"


def _set_db_error(message: str) -> None:
    st.session_state[DB_ERROR_KEY] = message


def _clear_db_error() -> None:
    st.session_state.pop(DB_ERROR_KEY, None)


def _safe_secret(key: str) -> str | None:
    try:
        value = st.secrets.get(key)
        return str(value).strip() if value else None
    except Exception:
        return None


def _sanitize_supabase_url(url: str) -> str:
    clean = url.strip().rstrip("/")
    rest_suffix = "/rest/v1"
    idx = clean.find(rest_suffix)
    if idx != -1:
        clean = clean[:idx].rstrip("/")
    return clean


def get_supabase_config() -> dict[str, str | bool | None]:
    raw_url = _safe_secret("SUPABASE_URL")
    legacy_key = _safe_secret("SUPABASE_KEY")
    service_role_key = _safe_secret("SUPABASE_SERVICE_ROLE_KEY") or legacy_key
    sanitized_url = _sanitize_supabase_url(raw_url) if raw_url else None

    return {
        "raw_url": raw_url,
        "sanitized_url": sanitized_url,
        "service_role_key": service_role_key,
        "used_legacy_key": bool(legacy_key and not _safe_secret("SUPABASE_SERVICE_ROLE_KEY")),
    }


def _get_supabase() -> Client | None:
    config = get_supabase_config()
    url = config["sanitized_url"]
    service_role_key = config["service_role_key"]

    if not url:
        _set_db_error("缺少 SUPABASE_URL，请在 Streamlit Secrets 中配置。")
        return None
    if not service_role_key:
        _set_db_error("缺少 SUPABASE_SERVICE_ROLE_KEY（或旧变量 SUPABASE_KEY），请在 Streamlit Secrets 中配置。")
        return None

    try:
        return create_client(url, service_role_key)
    except Exception as exc:
        _set_db_error(f"Supabase 客户端初始化失败: {exc}")
        return None


def fetch(table: str, **eq_filters):
    client = _get_supabase()
    if client is None:
        return []

    try:
        q = client.table(table).select("*")
        for k, v in eq_filters.items():
            if v is not None:
                q = q.eq(k, v)

        try:
            result = q.order("created_at", desc=True).execute()
        except APIError:
            result = q.execute()

        data = result.data or []
        _clear_db_error()
        return data
    except APIError as exc:
        _set_db_error(f"查询表 {table} 失败: {exc}")
        return []
    except Exception as exc:
        _set_db_error(f"查询表 {table} 异常: {exc}")
        return []


def insert(table: str, payload: dict[str, Any]):
    client = _get_supabase()
    if client is None:
        return None
    try:
        result = client.table(table).insert(payload).execute()
        _clear_db_error()
        return result
    except APIError as exc:
        _set_db_error(f"写入表 {table} 失败: {exc}")
        raise
    except Exception as exc:
        _set_db_error(f"写入表 {table} 异常: {exc}")
        raise


def upsert(table: str, payload: dict[str, Any], on_conflict: str | None = None):
    client = _get_supabase()
    if client is None:
        return None
    return client.table(table).upsert(payload, on_conflict=on_conflict).execute()


def update(table: str, row_id: str, payload: dict[str, Any]):
    client = _get_supabase()
    if client is None:
        return None
    return client.table(table).update(payload).eq("id", row_id).execute()
