import streamlit as st
from postgrest.exceptions import APIError

from app.supabase_client import get_supabase

TABLES = [
    "persons",
    "documents",
    "lab_results",
    "imaging_findings",
    "health_issues",
    "doctor_visits",
    "timeline_events",
    "extraction_jobs",
    "extracted_items",
]


def _show_status(ok: bool, label: str, detail: str = ""):
    prefix = "✅" if ok else "❌"
    msg = f"{prefix} {label}"
    if detail:
        msg = f"{msg}：{detail}"
    if ok:
        st.success(msg)
    else:
        st.error(msg)


def render():
    st.header("系统诊断")

    url = st.secrets.get("SUPABASE_URL")
    service_key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")

    _show_status(bool(url), "SUPABASE_URL 已配置")
    _show_status(bool(service_key), "SUPABASE_SERVICE_ROLE_KEY 已配置")

    if not url or not service_key:
        st.stop()

    try:
        client = get_supabase()
        client.table("persons").select("id").limit(1).execute()
        _show_status(True, "Supabase 连接成功")
    except Exception as exc:
        _show_status(False, "Supabase 连接失败", str(exc))
        st.stop()

    for table in TABLES:
        table_ok = True
        table_error = ""
        created_at_ok = False
        created_at_error = ""

        try:
            client.table(table).select("*").limit(1).execute()
        except APIError as exc:
            table_ok = False
            table_error = str(exc)
        except Exception as exc:
            table_ok = False
            table_error = str(exc)

        if table_ok:
            _show_status(True, f"表 {table} 存在且可访问")
            try:
                client.table(table).select("created_at").limit(1).execute()
                created_at_ok = True
            except Exception as exc:
                created_at_error = str(exc)
            _show_status(created_at_ok, f"表 {table} 包含 created_at 字段", created_at_error)
        else:
            _show_status(False, f"表 {table} 不可访问或不存在", table_error)
