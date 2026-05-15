from __future__ import annotations

import io
import json
from typing import Any

import streamlit as st
from google.cloud import vision
from google.oauth2 import service_account


SUPPORTED_IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}


def _build_vision_client() -> tuple[vision.ImageAnnotatorClient | None, str | None]:
    try:
        raw = st.secrets.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    except Exception:
        raw = None

    if not raw:
        return None, "图片 OCR 尚未配置，请在 Streamlit Secrets 中配置 Google Vision 服务账号 JSON。"

    try:
        info: dict[str, Any] = raw if isinstance(raw, dict) else json.loads(str(raw))
        credentials = service_account.Credentials.from_service_account_info(info)
        return vision.ImageAnnotatorClient(credentials=credentials), None
    except Exception as exc:
        return None, f"Google Vision 配置解析失败: {exc}"


def ocr_image_bytes(image_bytes: bytes, file_name: str = "") -> tuple[str, str | None]:
    client, err = _build_vision_client()
    if err:
        return "", err
    if not client:
        return "", "OCR 初始化失败。"

    try:
        image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=image)
        if response.error.message:
            return "", f"OCR 识别失败: {response.error.message}"
        text = (response.full_text_annotation.text or "").strip()
        if not text:
            return "", f"图片未识别到可用文字: {file_name or '未命名文件'}"
        return text, None
    except Exception as exc:
        return "", f"OCR 处理失败: {exc}"


def ocr_pixmap(pixmap: Any, page_index: int) -> tuple[str, str | None]:
    try:
        image_bytes = pixmap.tobytes("png")
        return ocr_image_bytes(image_bytes, f"page_{page_index + 1}.png")
    except Exception as exc:
        return "", f"页面渲染图 OCR 失败: {exc}"
