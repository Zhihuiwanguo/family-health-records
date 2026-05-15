from __future__ import annotations

import json
import os
from typing import Any

import requests

DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'


def analyze_text(ocr_text: str, file_name: str, person: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        return {'error': '未配置 DEEPSEEK_API_KEY'}

    payload = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': '你是严谨的医疗文档结构化助手，只输出合法 JSON。'},
            {
                'role': 'user',
                'content': (
                    '请根据输入文本输出 JSON，字段必须包含：report_type, report_date, summary, '
                    'abnormal_findings, risk_level, suggested_department, doctor_questions, '
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
        if content.startswith('```'):
            content = content.strip('`')
            content = content.replace('json\n', '', 1).strip()
        data = json.loads(content)
        return data if isinstance(data, dict) else {'error': 'DeepSeek 返回非对象 JSON'}
    except Exception as exc:
        return {'error': f'DeepSeek 分析失败: {exc}'}
