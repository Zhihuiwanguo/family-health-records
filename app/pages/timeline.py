import streamlit as st
from app import db


def render():
    st.header("时间轴")
    st.dataframe(db.fetch("timeline_events"))
