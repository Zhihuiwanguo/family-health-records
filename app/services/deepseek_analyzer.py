from __future__ import annotations

import json
import os
from typing import Any

import requests

DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'


def _empty_result() -> dict[str, Any]:
    return {
        'report_type': '',
        'report_date': '',
        'patient_name': '',
        'summary_for_family': '',
        'key_findings': [],
        'abnormal_findings': [],
        'risk_level_overall': '需医生判断',
        'suggested_department': [],
        'doctor_questions': [],
        'follow_up_suggestion': '',
        'health_event_title': '',
        'health_event_summary': '',
        'observations': [],
        'findings': [],
    }


def _normalize_result(raw: dict[str, Any], report_type: str, file_name: str) -> dict[str, Any]:
    result = _empty_result()
    result.update(raw or {})
    result['report_type'] = result.get('report_type') or report_type
    result['health_event_title'] = result.get('health_event_title') or f"{result['report_type']} - {file_name}"
    for key in ['key_findings', 'suggested_department', 'doctor_questions', 'abnormal_findings', 'observations', 'findings']:
        if not isinstance(result.get(key), list):
            result[key] = [str(result[key])] if result.get(key) else []
    return result


def _fallback_parse(content: str, report_type: str, file_name: str) -> dict[str, Any]:
    result = _empty_result()
    result['report_type'] = report_type
    result['summary_for_family'] = content[:1000]
    result['health_event_title'] = f'{report_type} - {file_name}'
    result['health_event_summary'] = content[:500]
    result['raw_response'] = content
    return result


def analyze_text(ocr_text: str, file_name: str, person: dict[str, Any], report_type: str) -> dict[str, Any]:
    if len((ocr_text or '').strip()) < 30:
        return {'error': '文字内容不足，无法可靠解读'}

    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        return {'error': '未配置 DEEPSEEK_API_KEY，请联系管理员配置后再试。', 'missing_api_key': True}

    prompt_focus = f'当前报告类型为「{report_type}」，请结合该类型重点解读异常指标、风险分层和就医准备问题。'
    payload = {
        'model': 'deepseek-chat',
        'response_format': {'type': 'json_object'},
        'messages': [
            {
                'role': 'system',
                'content': (
                    '你是家庭健康档案助手。你只能做报告解读和就医准备，不能替代医生诊断，'
                    '不能输出绝对诊断结论。对癌症、肿瘤、肺结节等高风险内容要谨慎表述，'
                    '必须使用条件性和建议性表达。输出必须是合法 JSON 对象。'
                ),
            },
            {
                'role': 'user',
                'content': (
                    '请严格输出 JSON 且包含字段：report_type, report_date, patient_name, summary_for_family, key_findings, abnormal_findings, observations, findings, risk_level_overall, suggested_department, doctor_questions, follow_up_suggestion, health_event_title, health_event_summary。\n'
                    'observations 必须覆盖报告中的全部检测项目（含正常项），每项包含 section_name,item_name,item_key,result_text,result_value,result_unit,reference_range,reference_low,reference_high,abnormal_flag,abnormal_direction,risk_level,interpretation,suggested_action,source_text,confidence。\n'
                    'findings 用于影像/描述性发现，包含 body_part,finding_name,finding_description,measurement_text,size_value,size_unit,risk_level,suggested_department,suggested_action,source_text,confidence。无法确定数值填 null，不要编造。\n'
                    f'{prompt_focus}\n'
                    f'人员信息: {json.dumps(person, ensure_ascii=False)}\n'
                    f'文件名: {file_name}\n'
                    f'OCR文本:\n{ocr_text[:14000]}'
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
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content'].strip()
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return {'error': 'DeepSeek 返回非对象 JSON', 'raw_response': content}
            return _normalize_result(data, report_type, file_name)
        except json.JSONDecodeError:
            fallback = _fallback_parse(content, report_type, file_name)
            fallback['error'] = 'DeepSeek 返回内容不是合法 JSON，已使用兜底解析。'
            return fallback
    except Exception as exc:
        return {'error': f'DeepSeek 分析失败: {exc}'}
