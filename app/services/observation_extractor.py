from __future__ import annotations

import re
from typing import Any

from app.services.deepseek_analyzer import analyze_text
from app.services.standard_item_map import normalize_item_key


def _to_float(v: Any) -> float | None:
    try:
        if v is None or v == '':
            return None
        m = re.search(r'-?\d+(?:\.\d+)?', str(v))
        return float(m.group()) if m else None
    except Exception:
        return None


def _extract_ref_range(text: str) -> tuple[float | None, float | None]:
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*[-~]\s*(-?\d+(?:\.\d+)?)', text or '')
    if not m:
        return None, None
    return _to_float(m.group(1)), _to_float(m.group(2))


def _rule_extract(ocr_text: str) -> list[dict[str, Any]]:
    rows = []
    for line in (ocr_text or '').splitlines():
        parts = [p.strip() for p in re.split(r'\s{2,}|\t|\|', line) if p.strip()]
        if len(parts) < 2:
            continue
        if any(k in line for k in ['项目', '结果', '参考', '单位', '检测结果']):
            continue
        item_name = parts[0]
        result_text = parts[1] if len(parts) > 1 else ''
        unit = parts[2] if len(parts) > 2 else ''
        ref = parts[3] if len(parts) > 3 else ''
        lo, hi = _extract_ref_range(ref)
        result_value = _to_float(result_text)
        abnormal_direction = ''
        abnormal_flag = ''
        if result_value is not None and lo is not None and result_value < lo:
            abnormal_direction, abnormal_flag = 'low', 'L'
        elif result_value is not None and hi is not None and result_value > hi:
            abnormal_direction, abnormal_flag = 'high', 'H'
        rows.append({
            'section_name': '', 'item_name': item_name, 'item_key': normalize_item_key(item_name), 'item_alias': '',
            'result_text': result_text, 'result_value': result_value, 'result_unit': unit,
            'reference_range': ref, 'reference_low': lo, 'reference_high': hi,
            'abnormal_flag': abnormal_flag, 'abnormal_direction': abnormal_direction,
            'risk_level': '', 'interpretation': '', 'suggested_action': '',
            'source_text': line[:500], 'confidence': 0.65,
        })
    return rows


def extract_observations_and_findings(ocr_text: str, report_type: str, report_date: str, person: dict[str, Any], file_name: str, person_id: str, file_id: str) -> dict[str, Any]:
    try:
        observations = _rule_extract(ocr_text)
        ai = analyze_text(ocr_text, file_name, person, report_type)
        ai_obs = ai.get('observations') if isinstance(ai, dict) else []
        ai_findings = ai.get('findings') if isinstance(ai, dict) else []
        if isinstance(ai_obs, list):
            for ob in ai_obs:
                if not isinstance(ob, dict) or not ob.get('item_name'):
                    continue
                ob['item_key'] = normalize_item_key(ob.get('item_key') or ob.get('item_name'))
                ob.setdefault('confidence', 0.5)
                observations.append(ob)
        # dedup by source text + item
        uniq = {}
        for ob in observations:
            k = f"{ob.get('item_name','')}|{ob.get('result_text','')}|{ob.get('source_text','')[:30]}"
            uniq[k] = ob
        return {
            'observations': list(uniq.values()),
            'findings': ai_findings if isinstance(ai_findings, list) else [],
            'message': '提取完成' if (uniq or ai_findings) else '未提取到稳定结构化指标，请人工补充。',
        }
    except Exception as exc:
        return {'observations': [], 'findings': [], 'message': f'提取失败：{exc}'}
