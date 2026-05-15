# 家庭健康档案工具（Streamlit + Supabase + DeepSeek）

> 仅用于健康资料整理，不提供医学诊断，不替代医生面诊、影像判读和治疗建议。

## 1) 创建 Supabase 项目
1. 登录 Supabase，创建新项目。
2. 在 **Project Settings -> API** 获取：
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

## 2) 执行建表 SQL
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

## 3) 配置 Streamlit Secrets
在 `.streamlit/secrets.toml`：

```toml
APP_PASSWORD = "your-strong-password"
DEEPSEEK_API_KEY = "sk-..."
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

## 4) 本地运行
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 5) 部署到 Streamlit Community Cloud
1. 代码推送到 GitHub 私有仓库（不要上传真实报告文件）。
2. 在 Streamlit Cloud 新建 App，选择该仓库和 `streamlit_app.py`。
3. 在 Secrets 中填入上述 4 个变量。
4. 部署后即可访问。

## 6) 隐私与医疗免责声明
- 默认会对姓名、手机号、身份证号、门诊号、住院号、检查号、影像号做脱敏。
- 调用 DeepSeek 前会明确提示：报告文本将发送到 DeepSeek API 用于结构化识别。
- AI 识别结果必须经人工确认后写入结构化表。
- 本工具不提供医学诊断或治疗建议。
