from __future__ import annotations

import json
import re
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from app import db
from app.supabase_client import get_supabase


OBS_COLUMNS = [
    'person_name', 'report_date', 'report_type', 'section_name', 'item_name', 'item_key', 'result_text',
    'result_value', 'result_unit', 'reference_range', 'abnormal_flag', 'interpretation', 'source_text',
]
FINDING_COLUMNS = [
    'person_name', 'report_date', 'report_type', 'body_part', 'finding_name', 'finding_description',
    'measurement_text', 'risk_level', 'suggested_department', 'suggested_action', 'source_text',
]

ALLOWED_FIELDS = {
    'health_files': {
        'person_id', 'file_name', 'file_type', 'upload_time', 'ai_summary', 'ai_json', 'raw_json',
        'confirmed', 'confirmed_at', 'ai_status',
    },
    'health_events': {
        'person_id', 'file_id', 'event_date', 'event_type', 'title', 'summary', 'risk_level',
        'department', 'confirmed', 'ai_json', 'raw_json',
    },
    'health_observations': {
        'person_id', 'file_id', 'report_date', 'report_type', 'section_name', 'item_name', 'item_key',
        'result_text', 'result_value', 'result_unit', 'reference_range', 'abnormal_flag',
        'interpretation', 'source_text', 'person_name', 'source_file', 'ai_json', 'raw_json',
    },
    'health_findings': {
        'person_id', 'file_id', 'report_date', 'report_type', 'body_part', 'finding_name',
        'finding_description', 'measurement_text', 'risk_level', 'suggested_department',
        'suggested_action', 'source_text', 'person_name', 'source_file', 'ai_json', 'raw_json',
    },
}


def _extract_missing_column(err: Exception) -> str | None:
    msg = str(err)
    m = re.search(r"Could not find the '([^']+)' column", msg)
    return m.group(1) if m else None


def _prepare_record(table: str, payload: dict, json_holder: str = 'ai_json') -> dict:
    allowed = ALLOWED_FIELDS[table]
    record = {k: v for k, v in payload.items() if k in allowed}
    extra = {k: v for k, v in payload.items() if k not in allowed}
    if extra and json_holder in allowed:
        existed = record.get(json_holder)
        if isinstance(existed, dict):
            record[json_holder] = {**existed, '_extra_fields': extra}
        elif existed:
            record[json_holder] = {'_original': existed, '_extra_fields': extra}
        else:
            record[json_holder] = {'_extra_fields': extra}
    elif extra and 'raw_json' in allowed and 'raw_json' not in record:
        record['raw_json'] = {'_extra_fields': extra}
    return record


def _safe_insert(sb, table: str, payload: dict | list[dict]):
    rows = payload if isinstance(payload, list) else [payload]
    rows = [_prepare_record(table, r) for r in rows]
    while True:
        try:
            return sb.table(table).insert(rows if isinstance(payload, list) else rows[0]).execute()
        except Exception as exc:
            missing_col = _extract_missing_column(exc)
            if not missing_col:
                raise
            for i, r in enumerate(rows):
                if missing_col in r:
                    removed = r.pop(missing_col)
                    holder = 'ai_json' if 'ai_json' in ALLOWED_FIELDS[table] else 'raw_json'
                    if holder in ALLOWED_FIELDS[table]:
                        current = r.get(holder)
                        if not isinstance(current, dict):
                            current = {'_original': current} if current else {}
                        dropped = current.get('_dropped_missing_columns', {})
                        dropped[missing_col] = removed
                        current['_dropped_missing_columns'] = dropped
                        r[holder] = current
                    rows[i] = r


def _load_persons() -> tuple[list[dict], dict[str, dict], dict[str, str]]:
    persons = db.fetch('persons')
    by_label = {f"{p.get('name') or p.get('full_name')} ({p['id']})": p for p in persons}
    by_name = {str((p.get('name') or p.get('full_name') or '')).strip(): p['id'] for p in persons}
    return persons, by_label, by_name


def _read_tabular(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    file_bytes = uploaded_file.read()
    return pd.read_excel(BytesIO(file_bytes))


def _insert_with_overwrite(sb, person_id: str, report_date: str, file_name: str, report_type: str, summary: str,
                           risk_level: str, department: str, file_info: dict, observations: list[dict], findings: list[dict],
                           overwrite: bool):
    existing = sb.table('health_files').select('id').eq('person_id', person_id).eq('upload_time', report_date).eq('file_name', file_name).limit(1).execute().data or []
    file_id = None
    if existing:
        file_id = existing[0]['id']
        if not overwrite:
            raise ValueError('已存在同 person_id + report_date + file_name 记录，请勾选“覆盖已存在记录”后重试。')
        sb.table('health_observations').delete().eq('file_id', file_id).execute()
        sb.table('health_findings').delete().eq('file_id', file_id).execute()
        sb.table('health_events').delete().eq('file_id', file_id).execute()
    else:
        inserted = _safe_insert(sb, 'health_files', {
            'person_id': person_id,
            'file_name': file_name,
            'file_type': report_type,
            'upload_time': report_date,
            'ai_summary': summary,
            'ai_json': file_info,
            'confirmed': True,
            'confirmed_at': datetime.utcnow().isoformat(),
            'ai_status': 'done',
        }).data or []
        file_id = inserted[0]['id'] if inserted else None

    if not file_id:
        raise ValueError('未能获取 file_id，导入中止。')

    if existing and overwrite:
        sb.table('health_files').update({
            'file_type': report_type, 'upload_time': report_date, 'ai_summary': summary, 'ai_json': file_info,
            'confirmed': True, 'confirmed_at': datetime.utcnow().isoformat(), 'ai_status': 'done',
        }).eq('id', file_id).execute()

    _safe_insert(sb, 'health_events', {
        'person_id': person_id,
        'file_id': file_id,
        'event_date': report_date,
        'event_type': 'manual_import',
        'title': file_name or report_type,
        'summary': summary,
        'risk_level': risk_level,
        'department': department,
        'confirmed': True,
    })

    if observations:
        _safe_insert(sb, 'health_observations', [{**x, 'person_id': person_id, 'file_id': file_id, 'report_date': report_date, 'report_type': report_type} for x in observations])
    if findings:
        _safe_insert(sb, 'health_findings', [{**x, 'person_id': person_id, 'file_id': file_id, 'report_date': report_date, 'report_type': report_type} for x in findings])


def render() -> None:
    st.header('V2 数据导入')
    try:
        _, by_label, by_name = _load_persons()
    except Exception as exc:
        st.error(f'加载人员失败: {exc}')
        return

    label = st.selectbox('1) 选择人员', list(by_label.keys()) if by_label else [])
    selected_person = by_label.get(label) if label else None
    if not selected_person:
        st.info('请先选择人员。')
        return

    st.subheader('2) JSON 导入')
    json_text = st.text_area('粘贴 ChatGPT 生成的 JSON', height=220)
    overwrite_json = st.checkbox('覆盖已存在记录（person_id + report_date + file_name）', key='ov_json')
    if st.button('预览 JSON', key='preview_json'):
        try:
            payload = json.loads(json_text)
            file_info = payload.get('file_info') or {}
            st.session_state['v2_json_payload'] = payload
            file_preview = _prepare_record('health_files', {
                'person_id': selected_person['id'],
                'file_name': file_info.get('file_name'),
                'file_type': file_info.get('report_type'),
                'upload_time': file_info.get('report_date'),
                'ai_summary': file_info.get('summary'),
                'ai_json': file_info,
            })
            obs_preview = [_prepare_record('health_observations', x) for x in (payload.get('observations') or [])]
            finding_preview = [_prepare_record('health_findings', x) for x in (payload.get('findings') or [])]
            st.caption('health_files 入库预览（已按白名单过滤，多余字段保存到 ai_json/raw_json）')
            st.dataframe(pd.DataFrame([file_preview]), use_container_width=True)
            st.caption('health_observations 入库预览')
            st.dataframe(pd.DataFrame(obs_preview), use_container_width=True)
            st.caption('health_findings 入库预览')
            st.dataframe(pd.DataFrame(finding_preview), use_container_width=True)
        except Exception as exc:
            st.error(f'JSON 解析失败: {exc}')

    if st.button('确认导入 JSON', type='primary'):
        try:
            payload = st.session_state.get('v2_json_payload') or json.loads(json_text)
            file_info = payload.get('file_info') or {}
            person_id = selected_person['id']
            report_date = file_info.get('report_date')
            report_type = file_info.get('report_type') or '未分类报告'
            file_name = file_info.get('file_name') or f"{report_type}_{report_date}"
            summary = file_info.get('summary') or ''
            risk_level = file_info.get('risk_level') or ''
            department = ','.join(file_info.get('suggested_department') or [])
            _insert_with_overwrite(get_supabase(), person_id, report_date, file_name, report_type, summary, risk_level, department, file_info,
                                   payload.get('observations') or [], payload.get('findings') or [], overwrite_json)
            st.success('JSON 导入成功。')
        except Exception as exc:
            st.error(f'JSON 导入失败: {exc}')

    st.subheader('3) CSV / Excel 导入')
    uploaded = st.file_uploader('上传 CSV 或 Excel', type=['csv', 'xlsx', 'xls'])
    data_kind = st.radio('数据类型', ['检测指标 observations', '影像发现 findings'], horizontal=True)
    overwrite_tab = st.checkbox('覆盖已存在记录（person_id + report_date + file_name）', key='ov_tab')

    if uploaded and st.button('预览表格', key='preview_tab'):
        try:
            df = _read_tabular(uploaded).fillna('')
            st.session_state['v2_import_df'] = df
            st.dataframe(df.head(100), use_container_width=True)
        except Exception as exc:
            st.error(f'文件解析失败: {exc}')

    if st.button('确认导入表格', key='import_tab', type='primary'):
        try:
            df = st.session_state.get('v2_import_df')
            if df is None or df.empty:
                raise ValueError('请先预览并确认有可导入数据。')
            kind = 'observations' if 'observations' in data_kind else 'findings'
            required = OBS_COLUMNS if kind == 'observations' else FINDING_COLUMNS
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(f'缺少必需字段: {missing}')
            sb = get_supabase()
            for _, row in df.iterrows():
                rowd = row.to_dict()
                pname = str(rowd.get('person_name', '')).strip()
                person_id = by_name.get(pname) or selected_person['id']
                report_date = str(rowd.get('report_date') or '')
                report_type = str(rowd.get('report_type') or '未分类报告')
                file_name = f"{report_type}_{report_date}_{pname or selected_person.get('name')}"
                file_info = {'person_name': pname, 'report_date': report_date, 'report_type': report_type, 'file_name': file_name}
                obs = [{k: rowd.get(k) for k in OBS_COLUMNS if k not in ('person_name', 'report_date', 'report_type')}] if kind == 'observations' else []
                finds = [{k: rowd.get(k) for k in FINDING_COLUMNS if k not in ('person_name', 'report_date', 'report_type')}] if kind == 'findings' else []
                _insert_with_overwrite(sb, person_id, report_date, file_name, report_type, '', str(rowd.get('risk_level') or ''), str(rowd.get('suggested_department') or ''), file_info, obs, finds, overwrite_tab)
            st.success('表格导入成功。')
        except Exception as exc:
            st.error(f'表格导入失败: {exc}')
