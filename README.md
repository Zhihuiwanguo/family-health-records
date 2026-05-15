# 家庭健康档案工具（Streamlit Cloud + Supabase + DeepSeek）

> 仅用于健康资料整理，不提供医学诊断，不替代医生面诊。

## 推荐流程（V2 半自动导入）

1. 用户将体检报告 / 检查报告（图片、PDF）发给 ChatGPT。
2. ChatGPT 输出标准 JSON 或 CSV/Excel。
3. 用户在 **V2 数据导入** 页面粘贴 JSON，或上传 CSV/Excel。
4. 系统导入后生成健康档案，支持时间轴与指标趋势对比。

## JSON 导入格式

```json
{
  "file_info": {
    "person_name": "父亲",
    "report_date": "2026-05-05",
    "report_type": "胸部CT",
    "hospital_name": "",
    "file_name": "",
    "summary": "",
    "risk_level": "",
    "suggested_department": [],
    "doctor_questions": [],
    "follow_up_suggestion": ""
  },
  "observations": [],
  "findings": []
}
```

- `file_info`：写入 `health_files` 与 `health_events`。
- `observations`：写入 `health_observations`。
- `findings`：写入 `health_findings`。
- 若同 `person_id + report_date + file_name` 已存在，可选择覆盖；覆盖会先删除对应 `file_id` 的旧 observations/findings 后重写。

## CSV/Excel 模板字段

### 检测指标（observations）
- `person_name`
- `report_date`
- `report_type`
- `section_name`
- `item_name`
- `item_key`
- `result_text`
- `result_value`
- `result_unit`
- `reference_range`
- `abnormal_flag`
- `interpretation`
- `source_text`

### 影像发现（findings）
- `person_name`
- `report_date`
- `report_type`
- `body_part`
- `finding_name`
- `finding_description`
- `measurement_text`
- `risk_level`
- `suggested_department`
- `suggested_action`
- `source_text`

## Streamlit Secrets 示例

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"
DEEPSEEK_API_KEY = "your_deepseek_api_key"
```

## Supabase 必要操作

1. 在 Supabase SQL Editor 执行：
   - `supabase/migrations/20260515_v2_health_archive.sql`
   - `supabase/migrations/20260516_v22_health_observations.sql`
   - `supabase/migrations/20260516_v24_manual_import.sql`
2. 在 Supabase Storage 创建 bucket：
   - `health-files`
3. 重启 Streamlit Cloud 应用

## 本地运行

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
