import streamlit as st
from app import db
from app.services import list_persons


def render():
    st.header("报告登记")
    persons = list_persons()
    options = {f"{p['name']} ({p['id']})": p["id"] for p in persons}
    with st.form("doc_form"):
        k = st.selectbox("所属人员", list(options.keys()) if options else [])
        payload = {
            "person_id": options[k] if options else None,
            "exam_date": str(st.date_input("检查日期")),
            "hospital": st.text_input("医院/机构"),
            "department": st.text_input("科室"),
            "report_type": st.text_input("报告类型"),
            "body_part": st.text_input("检查部位"),
            "drive_url": st.text_input("Google Drive 文件链接"),
            "file_name": st.text_input("文件名"),
            "notes": st.text_area("备注"),
            "is_critical": st.checkbox("是否关键报告"),
        }
        if st.form_submit_button("登记") and payload["person_id"]:
            db.insert("documents", payload)
            st.success("登记成功")
    st.dataframe(db.fetch("documents"))
