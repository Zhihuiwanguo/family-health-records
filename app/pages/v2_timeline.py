from __future__ import annotations

import json

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
        persons = db.fetch('persons')
        events = db.fetch('health_events')
        files = db.fetch('health_files')
    except Exception as exc:
        st.error(f'加载时间轴失败: {exc}')
        return

    options = {'全部': None}
    for p in persons:
        options[f"{p.get('name') or p.get('full_name')} ({p['id']})"] = p['id']
    selected = st.selectbox('按人员筛选', list(options.keys()))
    person_id = options[selected]

    filtered = [e for e in events if (not person_id or e.get('person_id') == person_id)]
    events_sorted = sorted(filtered, key=lambda x: x.get('event_date') or '', reverse=True)
    file_map = {f['id']: f for f in files}

    for evt in events_sorted:
        src_file = file_map.get(evt.get('file_id'), {})
        ai_json = _safe_json(evt.get('ai_json')) or _safe_json(src_file.get('ai_json'))
        with st.container(border=True):
            st.write(f"**日期**: {evt.get('event_date')}")
            st.write(f"**报告类型**: {evt.get('report_type') or ai_json.get('report_type') or '其他'}")
            st.write(f"**标题**: {evt.get('title')}")
            st.write(f"**摘要**: {evt.get('summary')}")
            st.write(f"**风险等级**: {evt.get('risk_level')}")
            st.write(f"**建议科室**: {evt.get('department')}")
            st.write(f"**来源文件名**: {src_file.get('file_name', '未知')}")
            with st.expander('展开详情'):
                st.write('**异常项列表**')
                for i, item in enumerate(ai_json.get('abnormal_findings') or [], 1):
                    text = item.get('item') if isinstance(item, dict) else str(item)
                    st.write(f'{i}. {text}')
                st.write('**医生问题清单**')
                for i, q in enumerate(ai_json.get('doctor_questions') or [], 1):
                    st.write(f'{i}. {q}')
                st.write(f"**复查建议**: {ai_json.get('follow_up_suggestion') or '暂无'}")
                raw = (src_file.get('ocr_text') or '')[:800]
                st.write('**OCR 原文摘要**')
                st.text(raw if raw else '暂无')

    st.divider()
    st.subheader('生成就诊摘要')
    if not person_id:
        st.info('请先选择具体人员。')
        return
    if st.button('生成就诊摘要', type='primary'):
        person = next((p for p in persons if p['id'] == person_id), None)
        person_events = [e for e in events_sorted if e.get('person_id') == person_id]
        main_abnormal, history, questions = [], [], []
        for e in person_events[:20]:
            aj = _safe_json(e.get('ai_json')) or _safe_json(file_map.get(e.get('file_id'), {}).get('ai_json'))
            if e.get('risk_level') in ['高', '中', 'high', 'medium']:
                main_abnormal.append(f"{e.get('event_date')} {e.get('title')}（{e.get('risk_level')}）")
            history.append(f"{e.get('event_date')} {e.get('report_type') or '检查'}")
            for q in aj.get('doctor_questions') or []:
                if isinstance(q, str) and q.strip():
                    questions.append(q.strip())
        summary = [
            f"基本情况：{person.get('name') or person.get('full_name')}，关系 {person.get('relation') or '未填写'}。",
            '近期主要异常：' + ('；'.join(main_abnormal[:8]) if main_abnormal else '暂无明确高风险记录。'),
            '历史相关检查：' + ('；'.join(history[:12]) if history else '暂无。'),
            '当前待确认问题：请结合本次主诉、复查节点和关键异常趋势与医生确认。',
            '建议向医生提问的问题：' + ('；'.join(questions[:10]) if questions else '是否需要进一步专科检查与随访。'),
        ]
        st.text_area('给医生看的摘要', value='\n'.join(summary), height=300)
