import streamlit as st
from app import db


def render():
    st.header("人员档案")
    with st.form("person_form"):
        name = st.text_input("姓名")
        relation = st.text_input("家庭关系")
        dob = st.date_input("出生日期", value=None)
        submit = st.form_submit_button("保存")
        if submit and name:
            db.insert("persons", {"name": name, "relation": relation, "dob": str(dob) if dob else None})
            st.success("已保存")
    st.dataframe(db.fetch("persons"))
