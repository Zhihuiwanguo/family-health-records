import streamlit as st
from app import db


def render():
    st.header("总览")
    metrics = [
        ("人员", "persons"),
        ("报告", "documents"),
        ("健康问题", "health_issues"),
        ("时间轴事件", "timeline_events"),
    ]

    counts: dict[str, int] = {}
    errors: list[str] = []
    for _, table in metrics:
        rows, err = db.fetch_with_status(table)
        counts[table] = len(rows)
        if err:
            errors.append(err.message)

    if errors:
        for msg in sorted(set(errors)):
            st.error(msg)

    cols = st.columns(4)
    cols[0].metric("人员", counts["persons"])
    cols[1].metric("报告", counts["documents"])
    cols[2].metric("健康问题", counts["health_issues"])
    cols[3].metric("时间轴事件", counts["timeline_events"])
