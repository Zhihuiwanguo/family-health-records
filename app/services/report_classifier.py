from __future__ import annotations


def classify_report_type(file_name: str, ocr_text: str) -> str:
    corpus = f"{file_name or ''}\n{ocr_text or ''}".lower()

    rules = [
        ("体检报告", ["体检", "健康体检"]),
        ("胸部CT", ["胸部ct", "肺部ct", "胸ct", "胸部平扫"]),
        ("影像报告", ["影像", "超声", "mri", "核磁", "dr", "x线"]),
        ("血常规", ["血常规", "wbc", "rbc", "hb", "hemoglobin"]),
        ("肝功能", ["肝功能", "alt", "ast", "总胆红素", "白蛋白"]),
        ("肾功能", ["肾功能", "肌酐", "尿素", "尿酸", "egfr"]),
        ("血脂", ["血脂", "甘油三酯", "胆固醇", "ldl", "hdl"]),
        ("血糖", ["血糖", "glucose", "糖化血红蛋白", "hba1c"]),
        ("尿常规", ["尿常规", "尿蛋白", "尿潜血", "尿比重"]),
        ("肿瘤标志物", ["肿瘤标志物", "cea", "afp", "ca19-9", "ca125"]),
        ("胃肠镜", ["胃镜", "肠镜", "结肠镜"]),
        ("病理报告", ["病理", "免疫组化", "切片"]),
        ("出院小结", ["出院小结", "出院记录", "出院诊断"]),
    ]

    for report_type, keywords in rules:
        if any(k in corpus for k in keywords):
            return report_type
    return "其他"
