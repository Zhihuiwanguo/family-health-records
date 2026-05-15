from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError(
            "未配置 SUPABASE_SERVICE_ROLE_KEY，请在 Streamlit Secrets 中配置 Supabase service_role key。"
        )
    if not url:
        raise RuntimeError("未配置 SUPABASE_URL，请在 Streamlit Secrets 中配置 Supabase URL。")
    return create_client(url, key)
