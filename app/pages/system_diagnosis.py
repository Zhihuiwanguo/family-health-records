import streamlit as st

from app import db


def _check_secret(name: str) -> tuple[bool, str]:
    try:
        value = st.secrets.get(name)
        if value and str(value).strip():
            return True, "已配置"
        return False, "未配置"
    except Exception as exc:
        return False, f"读取失败: {exc}"


def _check_table(table_name: str) -> tuple[bool, str]:
    rows = db.fetch(table_name)
    err = st.session_state.get("db_last_error")
    if err:
        return False, err
    return True, f"可读取，共 {len(rows)} 条"


def render():
    st.header("系统诊断")
    st.caption("用于快速检查 Supabase Secrets、连接与核心表可读性。")

    secret_checks = [
        ("SUPABASE_URL", *_check_secret("SUPABASE_URL")),
        ("SUPABASE_SERVICE_ROLE_KEY", *_check_secret("SUPABASE_SERVICE_ROLE_KEY")),
    ]

    st.subheader("Secrets 配置")
    for key, ok, summary in secret_checks:
        (st.success if ok else st.error)(f"{key}: {summary}")

    st.subheader("数据表读取")
    for table in ["persons", "documents"]:
        ok, summary = _check_table(table)
        if ok:
            st.success(f"{table}: {summary}")
        else:
            st.error(f"{table}: {summary}")
