import streamlit as st
from app import db


def render():
    st.header("医生摘要")
    dept = st.selectbox("选择摘要模板", ["胸外科", "肝病科/感染科", "心内科"])
    issues = db.fetch("health_issues")
    labs = db.fetch("lab_results")
    imgs = db.fetch("imaging_findings")
    st.write(f"### {dept} 摘要草稿")
    st.write("- 以下内容仅用于就诊前资料整理，不构成诊断建议。")
    st.write(f"- 实验室结果条目: {len(labs)}")
    st.write(f"- 影像发现条目: {len(imgs)}")
    st.write(f"- 健康问题条目: {len(issues)}")
