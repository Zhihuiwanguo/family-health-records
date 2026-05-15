import json
import streamlit as st
from app import db
from app.services import list_persons, list_documents
from app.ai.pdf_parser import extract_text_from_pdf
from app.ai.privacy import desensitize_text
from app.ai.deepseek_client import extract_structured


def render():
    st.header("AI识别中心")
    st.warning("调用DeepSeek前提示：报告文本将发送给DeepSeek API用于结构化识别。")
    model = st.selectbox("模型", ["deepseek-v4-pro", "deepseek-v4-flash"])
    persons = list_persons()
    po = {f"{p['name']} ({p['id']})": p['id'] for p in persons}
    pk = st.selectbox("1) 选择人员", list(po.keys()) if po else [])
    person_id = po[pk] if po else None
    docs = list_documents(person_id)
    do = {f"{d.get('file_name') or d['id']} ({d['id']})": d['id'] for d in docs}
    dk = st.selectbox("2) 选择已登记报告", list(do.keys()) if do else [])
    doc_id = do[dk] if do else None

    uploaded = st.file_uploader("3) 上传PDF", type=["pdf"])
    manual = st.text_area("或粘贴报告文本")
    raw_text = manual.strip()
    if uploaded:
        raw_text = extract_text_from_pdf(uploaded.read())

    if raw_text:
        st.text_area("4) 提取PDF文本/原文", raw_text, height=180)
        masked = desensitize_text(raw_text)
        st.text_area("5) 脱敏后预览", masked, height=180)
        consent = st.checkbox("6) 我确认发送脱敏文本给DeepSeek API")
        if st.button("7) 调用DeepSeek") and consent and person_id and doc_id:
            result = extract_structured(masked, model=model)
            st.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")
            job = db.insert("extraction_jobs", {"person_id": person_id, "document_id": doc_id, "raw_text": raw_text, "masked_text": masked, "status": "pending"}).data[0]
            db.insert("extracted_items", {"job_id": job["id"], "status": "pending", "payload": result})
            st.success("9) 已写入 extracted_items，状态 pending")

    st.subheader("10-11) 人工确认（简化版）")
    rows = db.fetch("extracted_items")
    for r in rows:
        st.write(f"Item {r['id']} / status={r['status']}")
        payload = r.get("payload", {})
        if st.button(f"确认入库 {r['id']}"):
            for x in payload.get("lab_results", []):
                db.insert("lab_results", x)
            for x in payload.get("imaging_findings", []):
                db.insert("imaging_findings", x)
            for x in payload.get("health_issues", []):
                db.insert("health_issues", x)
            for x in payload.get("followup_actions", []):
                db.insert("timeline_events", {"event_type": "followup", "summary": str(x)})
            db.update("extracted_items", r["id"], {"status": "confirmed"})
            st.success("已确认入库")
