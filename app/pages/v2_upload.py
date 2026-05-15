from __future__ import annotations

import json
from datetime import date

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
            ext = uploaded.name.lower().rsplit('.', 1)[-1]
            path = f"{person['id']}/{uploaded.name}"

            supabase = get_supabase()
            try:
                supabase.storage.from_('health-files').upload(path, file_bytes, {'content-type': uploaded.type})
            except Exception as exc:
                st.error('上传 Supabase Storage 失败，请确认 bucket `health-files` 已创建。')
                st.exception(exc)
                return

            ocr_text, ocr_status = extract_text(file_bytes, uploaded.name)
            if ocr_status == 'image_need_ocr':
                st.warning('图片OCR待接入，当前仅支持 PDF 文本直提。')

            file_row = {
                'person_id': person['id'],
                'file_name': uploaded.name,
                'file_type': ext,
                'storage_path': path,
                'ocr_text': ocr_text,
                'ocr_status': ocr_status,
                'ai_status': 'pending',
            }
            created = db.insert('health_files', file_row)
            health_file = (created.data or [])[0] if created else None

            ai_result = analyze_text(ocr_text, uploaded.name, person)
            if 'error' in ai_result:
                st.error(ai_result['error'])
                db.update('health_files', health_file['id'], {'ai_status': 'error', 'ai_summary': ai_result['error'], 'ai_json': ai_result})
            else:
                db.update(
                    'health_files',
                    health_file['id'],
                    {
                        'ai_status': 'done',
                        'ai_summary': ai_result.get('summary'),
                        'ai_json': ai_result,
                    },
                )

            st.subheader('待确认入档结果')
            st.write(f"文件名：{uploaded.name}")
            st.text_area('OCR 原文', ocr_text or '(空)', height=220)
            st.write('AI 摘要：', ai_result.get('summary') if isinstance(ai_result, dict) else '')
            st.json(ai_result)

            if st.button('确认入档'):
                try:
                    db.update(
                        'health_files',
                        health_file['id'],
                        {'confirmed': True, 'confirmed_at': __import__('datetime').datetime.utcnow().isoformat()},
                    )
                    event_date = ai_result.get('report_date') or date.today().isoformat()
                    event_payload = {
                        'person_id': person['id'],
                        'file_id': health_file['id'],
                        'event_date': event_date,
                        'event_type': ai_result.get('report_type') or 'medical_report',
                        'title': ai_result.get('report_type') or uploaded.name,
                        'summary': ai_result.get('summary') or '',
                        'risk_level': ai_result.get('risk_level') or 'unknown',
                        'department': ai_result.get('suggested_department') or None,
                        'confirmed': True,
                    }
                    db.insert('health_events', event_payload)
                    st.success('已保存到家庭健康档案')
                except Exception as exc:
                    st.error(f'确认入档失败: {exc}')
        except Exception as exc:
            st.error('处理失败，请查看错误详情。')
            st.exception(exc)
