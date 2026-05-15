from __future__ import annotations

import pandas as pd
import streamlit as st

from app import db


def render() -> None:
    st.header('V2 指标趋势')
    try:
        persons = db.fetch('persons')
        obs = db.fetch('health_observations')
    except Exception as exc:
        st.error(f'加载趋势数据失败: {exc}')
        return
    if not obs:
        st.info('暂无指标数据。')
        return
    pmap = {f"{p.get('name') or p.get('full_name')} ({p['id']})": p['id'] for p in persons}
    selected = st.selectbox('选择人员', list(pmap.keys()))
    person_obs = [x for x in obs if x.get('person_id') == pmap[selected]]
    keys = sorted({x.get('item_key') or x.get('item_name') for x in person_obs if x.get('item_name')})
    item = st.selectbox('选择指标', keys)
    only_abnormal = st.checkbox('仅看异常', value=False)
    rows = [x for x in person_obs if (x.get('item_key') or x.get('item_name')) == item]
    if only_abnormal:
        rows = [x for x in rows if x.get('abnormal_flag')]
    df = pd.DataFrame(rows)
    if df.empty:
        st.info('无可展示数据。'); return
    df = df.sort_values('report_date')
    st.dataframe(df[['report_date', 'item_name', 'item_key', 'result_value', 'result_text', 'result_unit', 'reference_range', 'reference_low', 'reference_high', 'abnormal_flag']], use_container_width=True)
    if 'result_value' in df.columns and df['result_value'].notna().any():
        chart_df = df[['report_date', 'result_value']].dropna()
        chart_df = chart_df.set_index('report_date')
        st.line_chart(chart_df)
        st.caption('参考范围以表格中的 reference_low / reference_high / reference_range 为准。')
