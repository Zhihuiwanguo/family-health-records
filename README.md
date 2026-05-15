# 家庭健康档案工具云端 MVP（Streamlit Cloud + Supabase + Google Drive 文件链接 + DeepSeek API）

> 仅用于健康资料整理，不提供医学诊断，不替代医生面诊、影像判读和治疗建议。

## 一、项目定位（云端 MVP）
本项目采用以下技术路线：
- **前端/应用层**：Streamlit Cloud 托管的 Streamlit 应用
- **结构化数据存储**：Supabase（PostgreSQL）
- **原始文件管理**：Google Drive 文件链接（系统仅保存链接与元数据）
- **AI 结构化识别**：DeepSeek API（通过兼容 OpenAI SDK 的方式调用）

该路线适合家庭成员体检/门诊资料的**轻量化云端管理**：
- 报告原文放在 Google Drive；
- 关键字段写入 Supabase；
- 通过 Streamlit 页面进行录入、审核和时间线查看。

## 二、创建 Supabase 项目
1. 登录 Supabase，创建新项目。
2. 在 **Project Settings -> API** 获取：
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

## 三、执行建表 SQL
在 Supabase SQL Editor 执行以下脚本：

```sql
create extension if not exists "pgcrypto";

create table if not exists persons (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  relation text,
  dob date,
  gender text,
  notes text,
  created_at timestamptz default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references persons(id) on delete cascade,
  exam_date date,
  hospital text,
  department text,
  report_type text,
  body_part text,
  drive_url text,
  file_name text,
  notes text,
  is_critical boolean default false,
  created_at timestamptz default now()
);

create table if not exists extraction_jobs (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references persons(id) on delete set null,
  document_id uuid references documents(id) on delete set null,
  raw_text text,
  masked_text text,
  model text,
  status text default 'pending',
  created_at timestamptz default now()
);

create table if not exists extracted_items (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references extraction_jobs(id) on delete cascade,
  payload jsonb not null,
  status text default 'pending',
  reviewer_note text,
  created_at timestamptz default now()
);

create table if not exists lab_results (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references persons(id) on delete set null,
  document_id uuid references documents(id) on delete set null,
  item_name text,
  item_value text,
  unit text,
  reference_range text,
  abnormal_flag text,
  exam_date date,
  created_at timestamptz default now()
);

create table if not exists imaging_findings (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references persons(id) on delete set null,
  document_id uuid references documents(id) on delete set null,
  modality text,
  body_part text,
  finding text,
  impression text,
  lesion_size text,
  suvmax text,
  exam_date date,
  created_at timestamptz default now()
);

create table if not exists health_issues (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references persons(id) on delete cascade,
  issue_name text not null,
  issue_category text,
  first_detected_date date,
  current_status text,
  risk_level text,
  latest_summary text,
  next_action text,
  followup_date date,
  is_closed_loop boolean default false,
  created_at timestamptz default now()
);

create table if not exists doctor_visits (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references persons(id) on delete cascade,
  visit_date date,
  department text,
  hospital text,
  doctor_name text,
  summary text,
  created_at timestamptz default now()
);

create table if not exists timeline_events (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references persons(id) on delete set null,
  document_id uuid references documents(id) on delete set null,
  event_date date,
  event_type text,
  summary text,
  source text,
  created_at timestamptz default now()
);
```

## 四、云端部署与 Secrets 配置
在 Streamlit Cloud 的 App `Secrets` 中配置（本地 `.streamlit/secrets.toml` 可使用相同键名）：

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"
DEEPSEEK_API_KEY = "your_deepseek_api_key"
```

注意事项：
- `SUPABASE_URL` 必须是项目根地址，不要带 `/rest/v1`。
- `SUPABASE_SERVICE_ROLE_KEY`（或兼容旧键名 `SUPABASE_KEY`）是敏感信息，不要提交到 GitHub。
- `supabase/migrations/20260515_fix_persons_documents_schema.sql` 需要复制到 Supabase SQL Editor 手动执行，本仓库不会自动改库。

## 五、本地开发运行（不与云端部署冲突）
本地开发与云端部署使用同一套代码和同一组 Secrets 键名，仅运行入口不同：

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

本地建议：
- 使用测试库或测试 schema，避免影响线上数据；
- 继续使用 Google Drive 链接字段（`drive_url`），不要求本地存储原始报告。

## 六、部署到 Streamlit Community Cloud
1. 代码推送到 GitHub 仓库（不要上传真实报告文件）。
2. 在 Streamlit Cloud 新建 App，入口选择 `streamlit_app.py`。
3. 在 Cloud 的 Secrets 中填入与本地相同的 4 个变量。
4. 部署后即可在线访问。

## 七、隐私与医疗免责声明
- 默认会对姓名、手机号、身份证号、门诊号、住院号、检查号、影像号做脱敏。
- 调用 DeepSeek 前会明确提示：报告文本将发送到 DeepSeek API 用于结构化识别。
- AI 识别结果必须经人工确认后写入结构化表。
- 本工具不提供医学诊断或治疗建议。
