import streamlit as st
from app import db


def render():
    st.header("健康问题追踪")
    st.dataframe(db.fetch("health_issues"))
