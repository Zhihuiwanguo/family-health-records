from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from app import db
from app.services.deepseek_analyzer import analyze_text
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
            file_bytes = uploaded.read()
            original_name = uploaded.name
            ext = Path(original_name).suffix.lower().lstrip('.')
            path = f"{person['id']}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.{ext}" if ext else f"{person['id']}/{uuid4().hex}"
            try:
                get_supabase().storage.from_('health-files').upload(path, file_bytes, {'content-type': uploaded.type or 'application/octet-stream', 'upsert': 'false'})
            except Exception as exc:
                st.error(f'上传 Supabase Storage 失败: {exc}')
                return

            ocr_text, ocr_status = extract_text(file_bytes, original_name)
            if ocr_status.startswith('scanned_pdf_ocr'):
                st.info('扫描 PDF 已进入 OCR 模式，可能较慢。')
            if ocr_status.startswith('image_ocr_error'):
                st.warning(ocr_status.split(':', 1)[-1].strip())

            report_type = classify_report_type(original_name, ocr_text)
            file_row = {
                'person_id': person['id'], 'file_name': original_name, 'file_type': ext, 'storage_path': path,
                'ocr_text': ocr_text, 'ocr_status': ocr_status, 'ai_status': 'pending', 'confirmed': False,
            }
            health_file = (db.insert('health_files', file_row).data or [None])[0]
            if not health_file:
                st.error('创建 health_files 记录失败。')
                return

            ai_result = analyze_text(ocr_text, original_name, person, report_type)
            ai_status = 'done' if 'error' not in ai_result else 'error'
            try:
                db.update('health_files', health_file['id'], {'ai_status': ai_status, 'ai_summary': ai_result.get('summary_for_family') or ai_result.get('error', ''), 'ai_json': ai_result})
            except Exception as exc:
                st.error(f'保存 AI 结果失败: {exc}')

            st.session_state['v2_upload_draft'] = {
                'health_file_id': health_file['id'], 'person_id': person['id'], 'file_name': original_name,
                'file_type': ext, 'ocr_status': ocr_status, 'ocr_text': ocr_text or '', 'report_type': report_type,
                'ai_result': ai_result if isinstance(ai_result, dict) else {},
            }
            st.success('上传并分析完成，请人工确认后入档。')
        except Exception as exc:
            st.error(f'处理失败: {exc}')

    draft = st.session_state.get('v2_upload_draft')
    if not draft:
        return

    ai_data = draft.get('ai_result', {})
    st.subheader('文件信息')
    st.write(f"原始文件名：{draft.get('file_name')}")
    st.write(f"文件类型：{draft.get('file_type')}")
    st.write(f"OCR 状态：{draft.get('ocr_status')}")
    st.write(f"识别报告类型：{draft.get('report_type')}")

    with st.expander('OCR 原文（可复制）', expanded=False):
        st.code(draft.get('ocr_text', ''), language='text')

    st.subheader('AI 解读结果（可编辑）')
    with st.form('v2_confirm_archive_form'):
        report_date = st.text_input('报告日期', value=ai_data.get('report_date') or date.today().isoformat())
        report_type = st.text_input('报告类型', value=ai_data.get('report_type') or draft.get('report_type') or '其他')
        summary_for_family = st.text_area('给家属看的摘要', value=ai_data.get('summary_for_family') or '')
        key_findings = st.text_area('关键发现（每行一条）', value='\n'.join(ai_data.get('key_findings') or []))
        abnormal_findings = st.text_area('异常项（每行一条）', value='\n'.join([x.get('item', '') if isinstance(x, dict) else str(x) for x in (ai_data.get('abnormal_findings') or [])]))
        risk_level_overall = st.selectbox('总体风险等级', ['低', '中', '高', '需医生判断'], index=['低', '中', '高', '需医生判断'].index(ai_data.get('risk_level_overall')) if ai_data.get('risk_level_overall') in ['低', '中', '高', '需医生判断'] else 3)
        suggested_department = st.text_area('建议科室（每行一条）', value='\n'.join(ai_data.get('suggested_department') or []))
        doctor_questions = st.text_area('建议问医生的问题（每行一条）', value='\n'.join(ai_data.get('doctor_questions') or []))
        follow_up_suggestion = st.text_area('复查建议', value=ai_data.get('follow_up_suggestion') or '')
        health_event_title = st.text_input('健康事件标题', value=ai_data.get('health_event_title') or draft.get('file_name'))
        health_event_summary = st.text_area('健康事件摘要', value=ai_data.get('health_event_summary') or summary_for_family)

        if st.form_submit_button('确认入档', type='primary'):
            try:
                final_ai_json = {
                    **ai_data,
                    'report_date': report_date,
                    'report_type': report_type,
                    'summary_for_family': summary_for_family,
                    'key_findings': [x.strip() for x in key_findings.splitlines() if x.strip()],
                    'abnormal_findings': [{'item': x.strip()} for x in abnormal_findings.splitlines() if x.strip()],
                    'risk_level_overall': risk_level_overall,
                    'suggested_department': [x.strip() for x in suggested_department.splitlines() if x.strip()],
                    'doctor_questions': [x.strip() for x in doctor_questions.splitlines() if x.strip()],
                    'follow_up_suggestion': follow_up_suggestion,
                    'health_event_title': health_event_title,
                    'health_event_summary': health_event_summary,
                }
                db.update('health_files', draft['health_file_id'], {
                    'ocr_text': draft.get('ocr_text', ''), 'ocr_status': draft.get('ocr_status'),
                    'ai_summary': summary_for_family, 'ai_json': final_ai_json, 'ai_status': 'done',
                    'confirmed': True, 'confirmed_at': datetime.utcnow().isoformat(),
                })
                db.insert('health_events', {
                    'person_id': draft['person_id'], 'file_id': draft['health_file_id'], 'event_date': report_date,
                    'event_type': 'report_analysis', 'report_type': report_type, 'title': health_event_title,
                    'summary': health_event_summary, 'risk_level': risk_level_overall,
                    'department': ', '.join(final_ai_json['suggested_department']) or None,
                    'ai_json': final_ai_json, 'confirmed': True,
                })
                st.success('已人工确认并入档。')
                st.session_state.pop('v2_upload_draft', None)
            except Exception as exc:
                st.error(f'确认入档失败: {exc}')
