from __future__ import annotations

import json
import re
import time
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
DEFAULT_BATCH_SIZE = 20
ERRNO_11_MAX_RETRIES = 3
ERRNO_11_SLEEP_SECONDS = 1


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


def _run_with_retry(action, errno_message: str):
    retries = 0
    while True:
        try:
            return action()
        except OSError as exc:
            if exc.errno == 11 and retries < ERRNO_11_MAX_RETRIES:
                retries += 1
                time.sleep(ERRNO_11_SLEEP_SECONDS)
                continue
            if exc.errno == 11:
                raise RuntimeError(errno_message) from exc
            raise


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
                           overwrite: bool, batch_size: int = DEFAULT_BATCH_SIZE):
    existing = sb.table('health_files').select('id').eq('person_id', person_id).eq('upload_time', report_date).eq('file_name', file_name).limit(1).execute().data or []
    file_id = None
    if existing:
        file_id = existing[0]['id']
        if not overwrite:
            raise ValueError('已存在同 person_id + report_date + file_name 记录，请勾选“覆盖已存在记录”后重试。')
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
        _run_with_retry(lambda: sb.table('health_files').update({
            'file_type': report_type, 'upload_time': report_date, 'ai_summary': summary, 'ai_json': file_info,
            'confirmed': True, 'confirmed_at': datetime.utcnow().isoformat(), 'ai_status': 'done',
        }).eq('id', file_id).execute(), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')

    if existing and overwrite:
        # 仅在新数据准备写入前执行删除；非事务模式下仍可能存在中途失败风险，页面会明确提示。
        _run_with_retry(lambda: sb.table('health_observations').delete().eq('file_id', file_id).execute(), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')
        _run_with_retry(lambda: sb.table('health_findings').delete().eq('file_id', file_id).execute(), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')
        _run_with_retry(lambda: sb.table('health_events').delete().eq('file_id', file_id).execute(), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')

    _run_with_retry(lambda: _safe_insert(sb, 'health_events', {
        'person_id': person_id,
        'file_id': file_id,
        'event_date': report_date,
        'event_type': 'manual_import',
        'title': file_name or report_type,
        'summary': summary,
        'risk_level': risk_level,
        'department': department,
        'confirmed': True,
    }), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')

    if observations:
        obs_rows = [{**x, 'person_id': person_id, 'file_id': file_id, 'report_date': report_date, 'report_type': report_type} for x in observations]
        obs_total = len(obs_rows)
        obs_progress = st.progress(0, text=f'health_observations 写入中：0/{obs_total}')
        for idx in range(0, obs_total, batch_size):
            batch = obs_rows[idx:idx + batch_size]
            _run_with_retry(lambda b=batch: _safe_insert(sb, 'health_observations', b), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')
            done = min(idx + batch_size, obs_total)
            obs_progress.progress(done / obs_total, text=f'health_observations 写入中：{done}/{obs_total}')
        obs_progress.empty()
    if findings:
        finding_rows = [{**x, 'person_id': person_id, 'file_id': file_id, 'report_date': report_date, 'report_type': report_type} for x in findings]
        finding_total = len(finding_rows)
        finding_progress = st.progress(0, text=f'health_findings 写入中：0/{finding_total}')
        for idx in range(0, finding_total, batch_size):
            batch = finding_rows[idx:idx + batch_size]
            _run_with_retry(lambda b=batch: _safe_insert(sb, 'health_findings', b), '导入过程中资源临时不可用，请稍后重试或减少单次导入数量。')
            done = min(idx + batch_size, finding_total)
            finding_progress.progress(done / finding_total, text=f'health_findings 写入中：{done}/{finding_total}')
        finding_progress.empty()


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
    uploaded_json = st.file_uploader('上传 JSON 文件（可选，优先于粘贴内容）', type=['json'], key='upload_json')
    json_text = st.text_area('粘贴 ChatGPT 生成的 JSON', height=220)
    overwrite_json = st.checkbox('覆盖已存在记录（person_id + report_date + file_name）', key='ov_json')
    st.caption('提示：当前覆盖导入不使用数据库事务。若中途失败，请重试导入以恢复完整数据。')

    def _read_json_payload() -> dict:
        if uploaded_json is not None:
            return json.loads(uploaded_json.getvalue().decode('utf-8'))
        return json.loads(json_text)

    if st.button('预览 JSON', key='preview_json'):
        try:
            payload = _read_json_payload()
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
            events_count = len(payload.get('events') or [])
            st.caption('导入摘要')
            st.write({
                'file_info': {
                    'person_name': file_info.get('person_name'),
                    'report_date': file_info.get('report_date'),
                    'report_type': file_info.get('report_type'),
                    'file_name': file_info.get('file_name'),
                },
                'observations_count': len(obs_preview),
                'findings_count': len(finding_preview),
                'events_count': events_count,
            })
            st.caption('health_files 入库预览（白名单过滤后）')
            st.dataframe(pd.DataFrame([file_preview]), use_container_width=True)
            st.caption('仅预览前 10 行（默认非编辑模式）')
            preview_obs_df = pd.DataFrame(obs_preview[:10])
            preview_finding_df = pd.DataFrame(finding_preview[:10])
            st.dataframe(preview_obs_df, use_container_width=True)
            st.dataframe(preview_finding_df, use_container_width=True)
            if st.checkbox('展开完整预览', key='expand_full_preview'):
                st.dataframe(pd.DataFrame(obs_preview), use_container_width=True)
                st.dataframe(pd.DataFrame(finding_preview), use_container_width=True)
        except Exception as exc:
            st.error(f'JSON 解析失败: {exc}')

    if st.button('确认导入 JSON', type='primary'):
        try:
            payload = st.session_state.get('v2_json_payload') or _read_json_payload()
            file_info = payload.get('file_info') or {}
            person_id = selected_person['id']
            report_date = file_info.get('report_date')
            report_type = file_info.get('report_type') or '未分类报告'
            file_name = file_info.get('file_name') or f"{report_type}_{report_date}"
            summary = file_info.get('summary') or ''
            risk_level = file_info.get('risk_level') or ''
            department = ','.join(file_info.get('suggested_department') or [])
            existing = get_supabase().table('health_files').select('id').eq('person_id', person_id).eq('upload_time', report_date).eq('file_name', file_name).limit(1).execute().data or []
            if existing and not overwrite_json:
                st.warning('检测到相同 person_name + report_date + file_name 记录，勾选“覆盖已存在记录”后可继续。')
                return
            _insert_with_overwrite(get_supabase(), person_id, report_date, file_name, report_type, summary, risk_level, department, file_info,
                                   payload.get('observations') or [], payload.get('findings') or [], overwrite_json, DEFAULT_BATCH_SIZE)
            st.success('JSON 导入成功。')
        except RuntimeError as exc:
            st.error(str(exc))
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
