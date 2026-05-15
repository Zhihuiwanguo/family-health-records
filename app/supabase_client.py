from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase() -> Client:
    raw_url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
    url = raw_url.split("/rest/v1", 1)[0].rstrip("/")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") or st.secrets.get("SUPABASE_KEY")
    if not key:
        raise KeyError("Missing SUPABASE_SERVICE_ROLE_KEY (or legacy SUPABASE_KEY)")
    return create_client(url, key)
