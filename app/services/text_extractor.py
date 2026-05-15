from __future__ import annotations

import io

import fitz

from app.services.ocr_service import SUPPORTED_IMAGE_TYPES, ocr_image_bytes, ocr_pixmap


MIN_TEXT_LENGTH = 80
MAX_OCR_PAGES = 10


def _extract_pdf_text_direct(file_bytes: bytes) -> str:
    text_parts: list[str] = []
    with fitz.open(stream=io.BytesIO(file_bytes), filetype='pdf') as doc:
        for page in doc:
            text_parts.append(page.get_text('text') or '')
    return '\n'.join(part.strip() for part in text_parts if part and part.strip()).strip()


def _extract_scanned_pdf_with_ocr(file_bytes: bytes) -> tuple[str, str]:
    all_pages: list[str] = []
    with fitz.open(stream=io.BytesIO(file_bytes), filetype='pdf') as doc:
        page_count = min(len(doc), MAX_OCR_PAGES)
        for i in range(page_count):
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_text, err = ocr_pixmap(pix, i)
            if err:
                all_pages.append(f"[第{i + 1}页OCR失败] {err}")
            elif page_text:
                all_pages.append(page_text)
    merged = '\n\n'.join(all_pages).strip()
    return merged, ('done' if merged else 'error')


def extract_text(file_bytes: bytes, file_name: str) -> tuple[str, str]:
    try:
        ext = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
        if ext == 'pdf':
            direct_text = _extract_pdf_text_direct(file_bytes)
            if len(direct_text) >= MIN_TEXT_LENGTH:
                return direct_text, 'done'
            ocr_text, ocr_status = _extract_scanned_pdf_with_ocr(file_bytes)
            return ocr_text, ('scanned_pdf_ocr_done' if ocr_status == 'done' else 'scanned_pdf_ocr_error')

        if ext in SUPPORTED_IMAGE_TYPES:
            text, err = ocr_image_bytes(file_bytes, file_name)
            if err:
                return '', f'image_ocr_error: {err}'
            return text, 'image_ocr_done'

        return '', 'unsupported_file_type'
    except Exception as exc:
        return f'提取失败: {exc}', 'error'
