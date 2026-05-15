from __future__ import annotations

import json
import os
from typing import Any

import requests

DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'
EXPECTED_FIELDS = [
    'report_type',
    'report_date',
    'title',
    'summary',
    'abnormal_findings',
    'risk_level',
    'suggested_department',
    'doctor_questions',
    'follow_up_suggestion',
    'structured_items',
]


def _empty_result() -> dict[str, Any]:
    return {
        'report_type': '',
        'report_date': '',
        'title': '',
        'summary': '',
        'abnormal_findings': [],
        'risk_level': 'unknown',
        'suggested_department': '',
        'doctor_questions': [],
        'follow_up_suggestion': '',
        'structured_items': [],
    }


def _normalize_result(raw: dict[str, Any]) -> dict[str, Any]:
    result = _empty_result()
    result.update({k: raw.get(k) for k in EXPECTED_FIELDS if k in raw})
    if not isinstance(result.get('abnormal_findings'), list):
        result['abnormal_findings'] = [str(result['abnormal_findings'])] if result.get('abnormal_findings') else []
    if not isinstance(result.get('doctor_questions'), list):
        result['doctor_questions'] = [str(result['doctor_questions'])] if result.get('doctor_questions') else []
    if not isinstance(result.get('structured_items'), list):
        result['structured_items'] = []
    return result


def _extract_json_text(content: str) -> str:
    clean = content.strip()
    if clean.startswith('```'):
        clean = clean.strip('`')
        clean = clean.replace('json\n', '', 1).strip()
    return clean


def _fallback_parse(content: str, file_name: str) -> dict[str, Any]:
    result = _empty_result()
    result['title'] = file_name
    result['summary'] = content[:1000]
    result['raw_response'] = content
    return result


def analyze_text(ocr_text: str, file_name: str, person: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        return {'error': '未配置 DEEPSEEK_API_KEY，请联系管理员配置后再试。', 'missing_api_key': True}

    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': '你是严谨的医疗文档结构化助手，只输出合法 JSON。'},
            {
                'role': 'user',
                'content': (
                    '请根据输入文本输出 JSON，字段必须包含：report_type, report_date, summary, '
                    'title, abnormal_findings, risk_level, suggested_department, doctor_questions, '
                    'follow_up_suggestion, structured_items。\n'
                    f'人员信息: {json.dumps(person, ensure_ascii=False)}\n'
                    f'文件名: {file_name}\n'
                    f'OCR文本:\n{ocr_text[:12000]}'
                ),
            },
        ],
        'temperature': 0.2,
    }

    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].strip()
        json_text = _extract_json_text(content)
        try:
            data = json.loads(json_text)
            if not isinstance(data, dict):
                return {'error': 'DeepSeek 返回非对象 JSON', 'raw_response': content}
            return _normalize_result(data)
        except json.JSONDecodeError:
            fallback = _fallback_parse(content, file_name)
            fallback['error'] = 'DeepSeek 返回内容不是合法 JSON，已使用兜底解析。'
            return fallback
    except Exception as exc:
        return {'error': f'DeepSeek 分析失败: {exc}'}
