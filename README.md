# 家庭健康档案工具 v1

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 设计约束

- 本地数据库：`data/health_records.db`
- 文件存储：`uploads/`
- 不调用外部 API
- 不上传云端
