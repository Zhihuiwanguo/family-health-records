from __future__ import annotations

import streamlit as st

from app import db


def render() -> None:
    st.header('V2 健康时间轴')
    try:
        persons = db.fetch('persons')
    except Exception as exc:
        st.error(f'加载人员失败: {exc}')
        return

    options = {'全部': None}
    for p in persons:
        options[f"{p.get('name') or p.get('full_name')} ({p['id']})"] = p['id']

    selected = st.selectbox('按人员筛选', list(options.keys()))
    person_id = options[selected]

    try:
        events = db.fetch('health_events', person_id=person_id) if person_id else db.fetch('health_events')
        files = db.fetch('health_files')
    except Exception as exc:
        st.error(f'加载时间轴失败: {exc}')
        return

    file_map = {f['id']: f for f in files}
    events_sorted = sorted(events, key=lambda x: x.get('event_date') or '', reverse=True)

    for evt in events_sorted:
        src_file = file_map.get(evt.get('file_id'), {})
        with st.container(border=True):
            st.write(f"**日期**: {evt.get('event_date')}")
            st.write(f"**标题**: {evt.get('title')}")
            st.write(f"**摘要**: {evt.get('summary')}")
            st.write(f"**风险等级**: {evt.get('risk_level')}")
            st.write(f"**建议科室**: {evt.get('department')}")
            st.write(f"**来源文件**: {src_file.get('file_name', '未知')}")
