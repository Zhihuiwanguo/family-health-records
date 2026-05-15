from __future__ import annotations

import pandas as pd
import streamlit as st

from app import db


ABNORMAL_VALUES = {'h', 'l', 'high', 'low', 'abnormal', '异常', '偏高', '偏低', '阳性', 'positive'}


def render() -> None:
    st.header('V2 指标趋势')
    try:
        persons = db.fetch('persons')
        obs = db.fetch('health_observations')
    except Exception as exc:
        st.error(f'加载趋势数据失败: {exc}')
        return

    if not persons:
        st.info('暂无人员数据。')
        return
    if not obs:
        st.info('暂无指标数据。')
        return

    pmap = {f"{p.get('name') or p.get('full_name')} ({p['id']})": p['id'] for p in persons}
    selected = st.selectbox('选择人员', list(pmap.keys()))
    person_obs = [x for x in obs if x.get('person_id') == pmap[selected]]
    if not person_obs:
        st.info('该人员暂无指标数据。')
        return

    keys = sorted({x.get('item_key') or x.get('item_name') for x in person_obs if x.get('item_key') or x.get('item_name')})
    item = st.selectbox('选择 item_key / item_name', keys)
    only_abnormal = st.checkbox('仅看异常指标', value=False)

    rows = [x for x in person_obs if (x.get('item_key') or x.get('item_name')) == item]
    if only_abnormal:
        rows = [x for x in rows if str(x.get('abnormal_flag', '')).strip().lower() in ABNORMAL_VALUES]

    df = pd.DataFrame(rows)
    if df.empty:
        st.info('无可展示数据。')
        return

    df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
    df = df.sort_values('report_date')

    show_cols = [
        'report_date', 'item_name', 'item_key', 'result_value', 'result_text', 'result_unit',
        'reference_range', 'reference_low', 'reference_high', 'abnormal_flag', 'interpretation'
    ]
    st.dataframe(df[[c for c in show_cols if c in df.columns]], use_container_width=True)

    numeric_series = pd.to_numeric(df.get('result_value'), errors='coerce')
    chart_df = pd.DataFrame({'report_date': df['report_date'], 'result_value': numeric_series}).dropna()
    if not chart_df.empty:
        st.line_chart(chart_df.set_index('report_date'))
        st.caption('仅当 result_value 为数值时展示趋势图。')
