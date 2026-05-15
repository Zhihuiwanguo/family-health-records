from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from app import db


def _safe_json(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def render() -> None:
    st.header('V2 健康时间轴')
    try:
        persons, events, files = db.fetch('persons'), db.fetch('health_events'), db.fetch('health_files')
        observations, findings = db.fetch('health_observations'), db.fetch('health_findings')
    except Exception as exc:
        st.error(f'加载时间轴失败: {exc}'); return
    options = {'全部': None, **{f"{p.get('name') or p.get('full_name')} ({p['id']})": p['id'] for p in persons}}
    person_id = options[st.selectbox('按人员筛选', list(options.keys()))]
    events_sorted = sorted([e for e in events if (not person_id or e.get('person_id') == person_id)], key=lambda x: x.get('event_date') or '', reverse=True)
    file_map = {f['id']: f for f in files}
    obs_by_file, find_by_file = {}, {}
    for o in observations: obs_by_file.setdefault(o.get('file_id'), []).append(o)
    for f in findings: find_by_file.setdefault(f.get('file_id'), []).append(f)
    for evt in events_sorted:
        src_file = file_map.get(evt.get('file_id'), {}); ai_json = _safe_json(evt.get('ai_json')) or _safe_json(src_file.get('ai_json'))
        with st.container(border=True):
            st.write(f"**日期**: {evt.get('event_date')} | **标题**: {evt.get('title')}")
            with st.expander('展开详情'):
                st.write(f"**报告摘要**: {evt.get('summary') or ai_json.get('summary_for_family') or '暂无'}")
                st.write('**异常指标**')
                abn = ai_json.get('abnormal_findings') or [x for x in obs_by_file.get(evt.get('file_id'), []) if x.get('abnormal_flag')]
                for i, item in enumerate(abn, 1): st.write(f"{i}. {item.get('item') if isinstance(item, dict) else str(item)}")
                st.write('**全部检测指标表**')
                st.dataframe(pd.DataFrame(obs_by_file.get(evt.get('file_id'), [])), use_container_width=True)
                st.write('**影像/描述性发现**')
                st.dataframe(pd.DataFrame(find_by_file.get(evt.get('file_id'), [])), use_container_width=True)
                st.write('**医生问题清单**')
                for i, q in enumerate(ai_json.get('doctor_questions') or [], 1): st.write(f'{i}. {q}')
                st.write(f"**来源文件**: {src_file.get('file_name', '未知')}")
