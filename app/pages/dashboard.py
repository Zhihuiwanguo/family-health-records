import streamlit as st
from app import db


def render():
    st.header("总览")

    persons = db.fetch("persons")
    documents = db.fetch("documents")
    issues = db.fetch("health_issues")
    events = db.fetch("timeline_events")

    cols = st.columns(4)
    cols[0].metric("人员", len(persons))
    cols[1].metric("报告", len(documents))
    cols[2].metric("健康问题", len(issues))
    cols[3].metric("时间轴事件", len(events))

    if st.session_state.get("db_last_error"):
        st.error("数据库连接或表结构异常，请检查 Supabase 建表 SQL、RLS、Secrets。")
