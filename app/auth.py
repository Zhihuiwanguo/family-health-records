from __future__ import annotations

import streamlit as st


def protect_page():
    st.sidebar.subheader("访问控制")
    if "authed" not in st.session_state:
        st.session_state.authed = False
    if not st.session_state.authed:
        pwd = st.sidebar.text_input("请输入访问密码", type="password")
        if st.sidebar.button("登录"):
            if pwd == st.secrets.get("APP_PASSWORD", ""):
                st.session_state.authed = True
                st.sidebar.success("登录成功")
            else:
                st.sidebar.error("密码错误")
        st.stop()

    if st.sidebar.button("退出登录"):
        st.session_state.authed = False
        st.rerun()
