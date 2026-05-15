# 家庭健康档案工具（Streamlit Cloud + Supabase + DeepSeek）

> 仅用于健康资料整理，不提供医学诊断，不替代医生面诊。

## V2 核心闭环

V2 已支持最小可用链路：

1. 上传 PDF / 图片
2. 文件写入 Supabase Storage（bucket: `health-files`）
3. 抽取 OCR 文本（PDF 文本直提）
4. 调用 DeepSeek 进行结构化解读
5. 页面展示 OCR 原文 + AI 结果
6. 用户人工点击“确认入档”
7. 写入家庭健康档案（`health_files` + `health_events`）
8. 可按人员查看健康时间轴

## Streamlit Secrets 示例

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"
DEEPSEEK_API_KEY = "your_deepseek_api_key"
```

## Supabase 必要操作

1. 在 Supabase SQL Editor 执行：
   - `supabase/migrations/20260515_v2_health_archive.sql`
2. 在 Supabase Storage 创建 bucket：
   - `health-files`
3. 重启 Streamlit Cloud 应用

## 本地运行

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 说明

- V2 首版图片 OCR 先返回占位状态（`image_need_ocr`）并在页面提示“图片OCR待接入”。
- 扫描版 PDF（提取不到文本）会标记 `scanned_pdf_need_ocr`。
- AI 结果不会自动入档，必须人工确认。
