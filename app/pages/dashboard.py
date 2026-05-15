import streamlit as st
from app import db


def render():
    st.header("总览")
    cols = st.columns(4)
    cols[0].metric("人员", len(db.fetch("persons")))
    cols[1].metric("报告", len(db.fetch("documents")))
    cols[2].metric("健康问题", len(db.fetch("health_issues")))
    cols[3].metric("时间轴事件", len(db.fetch("timeline_events")))
