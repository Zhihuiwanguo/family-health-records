from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from app import db
from app.services.deepseek_analyzer import analyze_text
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

    with st.expander('快速新增人员'):
        with st.form('v2_person_form'):
            name = st.text_input('姓名').strip()
            relation = st.text_input('关系').strip()
            dob = st.date_input('出生日期', value=None, min_value=date(1900, 1, 1), max_value=date.today())
            notes = st.text_area('备注').strip()
            if st.form_submit_button('新增人员'):
                if not name:
                    st.warning('姓名不能为空')
                else:
                    payload = {
                        'name': name,
                        'full_name': name,
                        'relation': relation or None,
                        'dob': dob.isoformat() if dob else None,
                        'notes': notes or None,
                    }
                    try:
                        db.insert('persons', payload)
                        st.success('新增人员成功，请刷新后选择。')
                    except Exception as exc:
                        st.error(f'新增人员失败: {exc}')

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
            unique_id = uuid4().hex
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{unique_id}.{ext}" if ext else f"{timestamp}_{unique_id}"
            path = f"{person['id']}/{unique_filename}"
            content_type = uploaded.type or 'application/octet-stream'

            supabase = get_supabase()
            try:
                supabase.storage.from_('health-files').upload(
                    path,
                    file_bytes,
                    {
                        'content-type': content_type,
                        'upsert': 'false',
                    },
                )
            except Exception as exc:
                if 'duplicate' in str(exc).lower() or 'already exists' in str(exc).lower():
                    st.error('文件路径重复，请重新上传或刷新页面')
                else:
                    st.error('上传 Supabase Storage 失败，请确认 bucket `health-files` 已创建。')
                    st.exception(exc)
                return

            ocr_text, ocr_status = extract_text(file_bytes, original_name)
            if ocr_status == 'image_need_ocr':
                st.warning('图片OCR待接入，当前仅支持 PDF 文本直提。')

            file_row = {
                'person_id': person['id'],
                'file_name': original_name,
                'file_type': ext,
                'storage_path': path,
                'ocr_text': ocr_text,
                'ocr_status': ocr_status,
                'ai_status': 'pending',
            }
            created = db.insert('health_files', file_row)
            health_file = (created.data or [])[0] if created else None
            if not health_file:
                st.error('创建 health_files 记录失败。')
                return

            ai_result = analyze_text(ocr_text, original_name, person)
            if 'error' in ai_result:
                st.error(ai_result['error'])
                try:
                    db.update('health_files', health_file['id'], {'ai_status': 'error', 'ai_summary': ai_result.get('summary') or ai_result['error'], 'ai_json': ai_result})
                except Exception as exc:
                    st.error(f'更新 AI 状态失败: {exc}')
            else:
                try:
                    db.update(
                        'health_files',
                        health_file['id'],
                        {
                            'ai_status': 'done',
                            'ai_summary': ai_result.get('summary'),
                            'ai_json': ai_result,
                        },
                    )
                except Exception as exc:
                    st.error(f'保存 AI 结果失败: {exc}')

            st.session_state['v2_upload_draft'] = {
                'health_file_id': health_file['id'],
                'person_id': person['id'],
                'file_name': original_name,
                'ocr_text': ocr_text or '',
                'ai_result': ai_result if isinstance(ai_result, dict) else {},
            }
            st.success('上传并分析完成，请确认入档。')
        except Exception as exc:
            st.error('处理失败，请查看错误详情。')
            st.exception(exc)

    draft = st.session_state.get('v2_upload_draft')
    if not draft:
        return

    st.subheader('待确认入档结果')
    st.write(f"文件名：{draft.get('file_name')}")
    st.text_area('OCR 原文', draft.get('ocr_text', ''), height=220, disabled=True)
    ai_data = draft.get('ai_result', {})
    with st.form('v2_confirm_archive_form'):
        title = st.text_input('标题', value=ai_data.get('title') or draft.get('file_name') or '')
        summary = st.text_area('AI 摘要', value=ai_data.get('summary') or '', height=100)
        abnormal_findings = st.text_area(
            '异常发现（每行一条）',
            value='\n'.join(ai_data.get('abnormal_findings') or []),
            height=100,
        )
        risk_level = st.selectbox('风险等级', ['low', 'medium', 'high', 'critical', 'unknown'], index=['low', 'medium', 'high', 'critical', 'unknown'].index((ai_data.get('risk_level') or 'unknown') if (ai_data.get('risk_level') or 'unknown') in ['low', 'medium', 'high', 'critical', 'unknown'] else 'unknown'))
        suggested_department = st.text_input('建议科室', value=ai_data.get('suggested_department') or '')
        doctor_questions = st.text_area(
            '医生问题清单（每行一条）',
            value='\n'.join(ai_data.get('doctor_questions') or []),
            height=120,
        )
        follow_up_suggestion = st.text_area('复查建议', value=ai_data.get('follow_up_suggestion') or '', height=100)
        report_type = st.text_input('报告类型', value=ai_data.get('report_type') or 'medical_report')
        report_date = st.text_input('报告日期 (YYYY-MM-DD)', value=ai_data.get('report_date') or date.today().isoformat())

        if st.form_submit_button('确认入档', type='primary'):
            try:
                abnormal_list = [x.strip() for x in abnormal_findings.splitlines() if x.strip()]
                doctor_q_list = [x.strip() for x in doctor_questions.splitlines() if x.strip()]
                final_ai_json = {
                    **ai_data,
                    'title': title,
                    'summary': summary,
                    'abnormal_findings': abnormal_list,
                    'risk_level': risk_level,
                    'suggested_department': suggested_department,
                    'doctor_questions': doctor_q_list,
                    'follow_up_suggestion': follow_up_suggestion,
                    'report_type': report_type,
                    'report_date': report_date,
                }
                db.update(
                    'health_files',
                    draft['health_file_id'],
                    {
                        'confirmed': True,
                        'confirmed_at': datetime.utcnow().isoformat(),
                        'ai_summary': summary,
                        'ai_json': final_ai_json,
                        'ai_status': 'done',
                    },
                )
                try:
                    event_date = report_date or date.today().isoformat()
                    event_payload = {
                        'person_id': draft['person_id'],
                        'file_id': draft['health_file_id'],
                        'event_date': event_date,
                        'event_type': report_type or 'medical_report',
                        'title': title or draft['file_name'],
                        'summary': summary or '',
                        'risk_level': risk_level or 'unknown',
                        'department': suggested_department or None,
                        'confirmed': True,
                    }
                    db.insert('health_events', event_payload)
                    st.success('已保存到家庭健康档案')
                    st.session_state.pop('v2_upload_draft', None)
                except Exception as exc:
                    st.error(f'写入 health_events 失败: {exc}')
            except Exception as exc:
                st.error(f'确认入档失败: {exc}')
