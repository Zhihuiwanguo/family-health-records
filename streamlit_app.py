import importlib

import streamlit as st

from app.auth import protect_page


PAGES = {
    "V2 上传分析": "app.pages.v2_upload",
    "V2 健康时间轴": "app.pages.v2_timeline",
    "V2 指标趋势": "app.pages.v2_trends",
    "系统诊断": "app.pages.system_diagnosis",
}

# 旧版功能暂时隐藏（含 AI识别中心），避免旧模块导入影响 V2 可用性。
LEGACY_PAGES = {
    "总览": "app.pages.dashboard",
    "人员档案": "app.pages.persons",
    "报告登记": "app.pages.documents",
    "AI识别中心": "app.pages.ai_extract",
    "健康问题追踪": "app.pages.issues",
    "时间轴": "app.pages.timeline",
    "医生摘要": "app.pages.doctor_summary",
}


st.set_page_config(page_title="家庭健康档案工具", layout="wide")
protect_page()

st.title("家庭健康档案工具（云端MVP）")
st.caption("仅用于健康资料整理，不提供医学诊断，不替代医生面诊。AI结果须人工确认后入库。")

page_name = st.sidebar.radio("导航", list(PAGES.keys()))
module_path = PAGES[page_name]

try:
    module = importlib.import_module(module_path)
    module.render()
except Exception as e:
    st.error(f"页面加载失败：{page_name}")
    st.exception(e)
