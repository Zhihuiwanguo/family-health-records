import streamlit as st
from ast import literal_eval

from app import db


def _parse_db_error_message(err: str) -> tuple[str | None, str | None, str | None, str]:
    message = code = hint = details = None
    if "{" in err and "}" in err:
        try:
            body = literal_eval(err[err.find("{") : err.rfind("}") + 1])
            if isinstance(body, dict):
                message = body.get("message")
                code = body.get("code")
                hint = body.get("hint")
                details = body.get("details")
        except Exception:
            pass
    return message, code, hint, details or err


def _check_table(table_name: str) -> tuple[bool, str]:
    rows = db.fetch(table_name)
    err = st.session_state.get("db_last_error")
    if err:
        message, code, hint, details = _parse_db_error_message(err)
        parts = [f"错误: {err}"]
        if message:
            parts.append(f"message: {message}")
        if code:
            parts.append(f"code: {code}")
        if hint:
            parts.append(f"hint: {hint}")
        if details:
            parts.append(f"details: {details}")
        return False, "\n".join(parts)
    return True, f"可读取，共 {len(rows)} 条"


def render():
    st.header("系统诊断")
    st.caption("用于快速检查 Supabase Secrets、连接与核心表可读性。")

    cfg = db.get_supabase_config()
    raw_url = str(cfg["raw_url"] or "")
    sanitized_url = str(cfg["sanitized_url"] or "")
    key = str(cfg["service_role_key"] or "")
    has_url = bool(raw_url)
    has_key = bool(key)

    st.subheader("Secrets 配置")
    (st.success if has_url else st.error)(f"SUPABASE_URL: {'已配置' if has_url else '未配置'}")
    if has_url and raw_url != sanitized_url:
        st.warning(f"SUPABASE_URL 检测到包含 /rest/v1 或多余斜杠，已自动规范化为: {sanitized_url}")
    elif has_url:
        st.info(f"SUPABASE_URL 格式正常: {sanitized_url}")

    masked_key = f"{key[:4]}****" if has_key else "未配置"
    (st.success if has_key else st.error)(f"SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY: {'已配置' if has_key else '未配置'} ({masked_key})")

    st.subheader("数据表读取")
    for table in ["persons", "documents"]:
        ok, summary = _check_table(table)
        if ok:
            st.success(f"{table}: {summary}")
        else:
            st.error(f"{table}: {summary}")
