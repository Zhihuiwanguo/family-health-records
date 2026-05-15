import streamlit as st
from datetime import date
from app import db


def render():
    st.header("人员档案")
    with st.form("person_form"):
        name = st.text_input("姓名")
        relation = st.text_input("家庭关系")
        birth_date = st.date_input(
            "出生日期",
            value=None,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
            key="person_birth_date",
        )
        submit = st.form_submit_button("保存")
        if submit and name:
            birth_date_value = birth_date.isoformat() if birth_date else None
            db.insert("persons", {"name": name, "relation": relation, "dob": birth_date_value})
            st.success("已保存")
    st.dataframe(db.fetch("persons"))
