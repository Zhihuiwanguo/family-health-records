from __future__ import annotations

import io

import fitz


def extract_text(file_bytes: bytes, file_name: str) -> tuple[str, str]:
    try:
        ext = file_name.lower().rsplit('.', 1)[-1] if '.' in file_name else ''
        if ext == 'pdf':
            text_parts: list[str] = []
            with fitz.open(stream=io.BytesIO(file_bytes), filetype='pdf') as doc:
                for page in doc:
                    text_parts.append(page.get_text('text') or '')
            text = '\n'.join(part.strip() for part in text_parts if part and part.strip()).strip()
            if not text:
                return '', 'scanned_pdf_need_ocr'
            return text, 'done'

        if ext in {'png', 'jpg', 'jpeg', 'webp'}:
            return '图片OCR待接入', 'image_need_ocr'

        return '', 'unsupported_file_type'
    except Exception as exc:
        return f'提取失败: {exc}', 'error'
