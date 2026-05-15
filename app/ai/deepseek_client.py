from __future__ import annotations

import streamlit as st
from openai import OpenAI
from app.ai.prompts import SYSTEM_PROMPT
from app.utils import safe_json_loads


def extract_structured(text: str, model: str = "deepseek-v4-pro") -> dict:
    client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请结构化以下报告文本:\n{text}"},
        ],
        temperature=0.1,
    )
    content = resp.choices[0].message.content
    return safe_json_loads(content)
