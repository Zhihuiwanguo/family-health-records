from __future__ import annotations

from app import db


def list_persons():
    return db.fetch("persons")


def list_documents(person_id: str | None = None):
    return db.fetch("documents", person_id=person_id)


def create_extraction_job(person_id: str, document_id: str, raw_text: str, masked_text: str):
    return db.insert(
        "extraction_jobs",
        {
            "person_id": person_id,
            "document_id": document_id,
            "raw_text": raw_text,
            "masked_text": masked_text,
            "status": "pending",
        },
    )


def add_extracted_items(job_id: str, payload: dict):
    return db.insert("extracted_items", {"job_id": job_id, "status": "pending", "payload": payload})
