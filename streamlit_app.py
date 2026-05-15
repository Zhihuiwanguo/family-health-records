import streamlit as st
from app.auth import protect_page
from app.pages import dashboard, persons, documents, ai_extract, issues, timeline, doctor_summary, system_diagnosis

st.set_page_config(page_title="家庭健康档案工具", layout="wide")
protect_page()

st.title("家庭健康档案工具（云端MVP）")
st.caption("仅用于健康资料整理，不提供医学诊断，不替代医生面诊。AI结果须人工确认后入库。")

page = st.sidebar.radio(
    "导航",
    ["总览", "人员档案", "报告登记", "AI识别中心", "健康问题追踪", "时间轴", "医生摘要", "系统诊断"],
)

if page == "总览":
    dashboard.render()
elif page == "人员档案":
    persons.render()
elif page == "报告登记":
    documents.render()
elif page == "AI识别中心":
    ai_extract.render()
elif page == "健康问题追踪":
    issues.render()
elif page == "时间轴":
    timeline.render()
elif page == "医生摘要":
    doctor_summary.render()
else:
    system_diagnosis.render()
