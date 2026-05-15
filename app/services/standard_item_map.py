from __future__ import annotations

import re

STANDARD_ITEM_MAP = {
    '白细胞计数': 'WBC', 'wbc': 'WBC', '白细胞': 'WBC',
    '红细胞计数': 'RBC', 'rbc': 'RBC', '红细胞': 'RBC',
    '血红蛋白': 'HGB', 'hgb': 'HGB', 'hb': 'HGB',
    '血小板': 'PLT', 'plt': 'PLT',
    '谷丙转氨酶': 'ALT', 'alt': 'ALT',
    '谷草转氨酶': 'AST', 'ast': 'AST',
    '总胆红素': 'TBIL', 'tbil': 'TBIL',
    '肌酐': 'CREA', 'crea': 'CREA', 'scr': 'CREA',
    '尿酸': 'UA', 'ua': 'UA',
    '空腹血糖': 'GLU', 'glu': 'GLU', '葡萄糖': 'GLU',
    '总胆固醇': 'TC', 'tc': 'TC',
    '甘油三酯': 'TG', 'tg': 'TG',
    '高密度脂蛋白胆固醇': 'HDL_C', 'hdl-c': 'HDL_C',
    '低密度脂蛋白胆固醇': 'LDL_C', 'ldl-c': 'LDL_C',
    'c反应蛋白': 'CRP', 'crp': 'CRP',
    '癌胚抗原': 'CEA', 'cea': 'CEA',
    '甲胎蛋白': 'AFP', 'afp': 'AFP',
}


def normalize_item_key(item_name: str | None) -> str:
    if not item_name:
        return ''
    raw = str(item_name).strip()
    key = raw.lower().replace(' ', '')
    mapped = STANDARD_ITEM_MAP.get(key) or STANDARD_ITEM_MAP.get(raw)
    if mapped:
        return mapped
    normalized = re.sub(r'[^\w\u4e00-\u9fff]+', '_', raw).strip('_')
    return normalized.upper()
