from __future__ import annotations

import json

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
            with st.expander('展开详情'):
                ai_json = src_file.get('ai_json') or {}
                if isinstance(ai_json, str):
                    try:
                        ai_json = json.loads(ai_json)
                    except Exception:
                        ai_json = {'raw': ai_json}
                st.write('**医生问题清单**')
                questions = ai_json.get('doctor_questions') if isinstance(ai_json, dict) else None
                if isinstance(questions, list) and questions:
                    for idx, q in enumerate(questions, start=1):
                        st.write(f'{idx}. {q}')
                else:
                    st.write('暂无')
                st.json(ai_json)

    st.divider()
    st.subheader('就诊摘要')
    if not person_id:
        st.info('请先选择具体人员，再生成就诊摘要。')
        return
    if st.button('生成就诊摘要', type='primary'):
        person = next((p for p in persons if p['id'] == person_id), None)
        if not person:
            st.error('未找到人员信息。')
            return
        person_events = [e for e in events_sorted if e.get('person_id') == person_id]
        recent_abnormal = [e for e in person_events if (e.get('risk_level') or '').lower() in {'high', 'critical', 'medium'}][:5]
        history_checks = person_events[:10]
        concern_questions: list[str] = []
        for e in person_events:
            f = file_map.get(e.get('file_id'), {})
            ai_json = f.get('ai_json') or {}
            if isinstance(ai_json, dict):
                for q in (ai_json.get('doctor_questions') or []):
                    if isinstance(q, str) and q.strip():
                        concern_questions.append(q.strip())
        summary_lines = [
            f"基本信息：{person.get('name') or person.get('full_name')}，关系：{person.get('relation') or '未填写'}，出生日期：{person.get('dob') or '未填写'}。",
            "近期异常：" + ("；".join([f"{e.get('event_date')} {e.get('title')}（风险{e.get('risk_level')}）" for e in recent_abnormal]) if recent_abnormal else "暂无明确高风险异常。"),
            "历史相关检查：" + ("；".join([f"{e.get('event_date')} {e.get('title')}" for e in history_checks]) if history_checks else "暂无。"),
            "当前关注问题：" + ("；".join([e.get('summary') or '' for e in recent_abnormal if e.get('summary')]) or "请结合主诉与近期指标变化综合判断。"),
            "建议向医生确认的问题：" + ("；".join(concern_questions[:8]) if concern_questions else "是否需要进一步专科检查和复查计划。"),
        ]
        st.text_area('给医生的就诊摘要', value='\n'.join(summary_lines), height=260)
