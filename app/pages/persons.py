import streamlit as st
from datetime import date
from postgrest.exceptions import APIError
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
        if submit:
            if not name.strip():
                st.error("姓名不能为空。")
                return
            birth_date_value = birth_date.isoformat() if birth_date else None
            payload = {
                "full_name": name.strip(),
                "name": name.strip(),
                "relation": relation.strip() if relation else None,
                "dob": birth_date_value,
            }
            try:
                db.insert("persons", payload)
                st.success("已保存")
            except APIError as exc:
                st.error("新增人员失败，请检查 persons 表字段并查看下方异常详情。")
                st.exception(exc)
            except Exception as exc:
                st.error("新增人员失败，请检查 persons 表字段并查看下方异常详情。")
                st.exception(exc)
    st.dataframe(db.fetch("persons"))
