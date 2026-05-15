from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from app import db
from app.services.observation_extractor import extract_observations_and_findings
from app.services.report_classifier import classify_report_type
from app.services.text_extractor import extract_text
from app.supabase_client import get_supabase


def _load_persons() -> list[dict]:
    try:
        return db.fetch('persons')
    except Exception as exc:
        st.error(f'加载人员失败: {exc}')
        return []


def render() -> None:
    st.header('V2 上传分析')
    persons = _load_persons()
    person_options = {f"{p.get('name') or p.get('full_name')} ({p['id']})": p for p in persons}
    selected_label = st.selectbox('选择人员', list(person_options.keys()) if person_options else [])
    person = person_options[selected_label] if selected_label else None
    uploaded = st.file_uploader('上传报告文件', type=['pdf', 'png', 'jpg', 'jpeg', 'webp'])
    if not uploaded or not person:
        return
    if st.button('开始上传并分析', type='primary'):
        try:
            file_bytes = uploaded.read(); original_name = uploaded.name
            ext = Path(original_name).suffix.lower().lstrip('.')
            path = f"{person['id']}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.{ext}" if ext else f"{person['id']}/{uuid4().hex}"
            get_supabase().storage.from_('health-files').upload(path, file_bytes, {'content-type': uploaded.type or 'application/octet-stream', 'upsert': 'false'})
            ocr_text, ocr_status = extract_text(file_bytes, original_name)
            report_type = classify_report_type(original_name, ocr_text)
            health_file = (db.insert('health_files', {'person_id': person['id'], 'file_name': original_name, 'file_type': ext, 'storage_path': path, 'ocr_text': ocr_text, 'ocr_status': ocr_status, 'ai_status': 'pending', 'confirmed': False}).data or [None])[0]
            parsed = extract_observations_and_findings(ocr_text, report_type, date.today().isoformat(), person, original_name, person['id'], health_file['id'])
            ai_json = {'report_type': report_type, 'report_date': date.today().isoformat(), 'summary_for_family': parsed.get('message', ''), 'observations': parsed.get('observations', []), 'findings': parsed.get('findings', []), 'doctor_questions': [], 'abnormal_findings': []}
            db.update('health_files', health_file['id'], {'ai_status': 'done', 'ai_summary': ai_json.get('summary_for_family', ''), 'ai_json': ai_json})
            st.session_state['v2_upload_draft'] = {'health_file_id': health_file['id'], 'person_id': person['id'], 'file_name': original_name, 'file_type': ext, 'ocr_status': ocr_status, 'ocr_text': ocr_text or '', 'report_type': report_type, 'ai_result': ai_json}
            st.success('上传并分析完成，请人工确认后入档。')
        except Exception as exc:
            st.error(f'处理失败: {exc}')

    draft = st.session_state.get('v2_upload_draft')
    if not draft:
        return
    ai_data = draft.get('ai_result', {})
    st.subheader('OCR 原文'); st.text_area('OCR 原文', value=draft.get('ocr_text', ''), height=180)
    st.subheader('报告整体解读'); summary_for_family = st.text_area('摘要', value=ai_data.get('summary_for_family', ''), height=120)

    obs_df = pd.DataFrame(ai_data.get('observations') or [])
    if obs_df.empty:
        obs_df = pd.DataFrame(columns=['item_name', 'item_key', 'result_text', 'result_value', 'result_unit', 'reference_range', 'abnormal_flag', 'interpretation'])
    st.subheader('检测指标明细表')
    edited_obs = st.data_editor(obs_df, num_rows='dynamic', use_container_width=True)

    find_df = pd.DataFrame(ai_data.get('findings') or [])
    if find_df.empty:
        find_df = pd.DataFrame(columns=['body_part', 'finding_name', 'finding_description', 'measurement_text', 'risk_level', 'suggested_action'])
    st.subheader('影像/描述性发现')
    edited_findings = st.data_editor(find_df, num_rows='dynamic', use_container_width=True)

    if st.button('确认入档', type='primary'):
        try:
            final_ai_json = {**ai_data, 'summary_for_family': summary_for_family, 'observations': edited_obs.fillna('').to_dict('records'), 'findings': edited_findings.fillna('').to_dict('records')}
            db.update('health_files', draft['health_file_id'], {'ocr_text': draft.get('ocr_text', ''), 'ocr_status': draft.get('ocr_status'), 'ai_summary': summary_for_family, 'ai_json': final_ai_json, 'ai_status': 'done', 'confirmed': True, 'confirmed_at': datetime.utcnow().isoformat()})
            db.insert('health_events', {'person_id': draft['person_id'], 'file_id': draft['health_file_id'], 'event_date': ai_data.get('report_date') or date.today().isoformat(), 'event_type': 'report_analysis', 'report_type': ai_data.get('report_type') or draft.get('report_type'), 'title': ai_data.get('health_event_title') or draft.get('file_name'), 'summary': ai_data.get('health_event_summary') or summary_for_family, 'risk_level': ai_data.get('risk_level_overall') or '需医生判断', 'department': ', '.join(ai_data.get('suggested_department') or []), 'ai_json': final_ai_json, 'confirmed': True})
            sb = get_supabase()
            try:
                sb.table('health_observations').delete().eq('file_id', draft['health_file_id']).execute()
                sb.table('health_findings').delete().eq('file_id', draft['health_file_id']).execute()
            except Exception as exc:
                st.error(f'清理旧明细失败: {exc}')
            obs_rows = [{**row, 'person_id': draft['person_id'], 'file_id': draft['health_file_id'], 'report_date': ai_data.get('report_date') or date.today().isoformat(), 'report_type': ai_data.get('report_type') or draft.get('report_type')} for row in final_ai_json.get('observations', []) if row.get('item_name')]
            finding_rows = [{**row, 'person_id': draft['person_id'], 'file_id': draft['health_file_id'], 'report_date': ai_data.get('report_date') or date.today().isoformat(), 'report_type': ai_data.get('report_type') or draft.get('report_type')} for row in final_ai_json.get('findings', [])]
            if obs_rows:
                sb.table('health_observations').insert(obs_rows).execute()
            if finding_rows:
                sb.table('health_findings').insert(finding_rows).execute()
            st.success('已人工确认并入档。')
        except Exception as exc:
            st.error(f'确认入档失败: {exc}')
