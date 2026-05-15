from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Iterable

import streamlit as st

DB_PATH = Path("data/health_records.db")
UPLOAD_DIR = Path("uploads")


def ensure_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gender TEXT,
                birth_date TEXT,
                phone TEXT,
                relation TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                report_date TEXT,
                report_type TEXT,
                title TEXT,
                file_path TEXT,
                file_name TEXT,
                source TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES persons(id)
            );

            CREATE TABLE IF NOT EXISTS manual_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                entry_date TEXT,
                category TEXT NOT NULL,
                item_name TEXT,
                value_text TEXT,
                conclusion TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES persons(id)
            );

            CREATE TABLE IF NOT EXISTS health_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                issue_name TEXT NOT NULL,
                severity TEXT,
                status TEXT,
                start_date TEXT,
                next_follow_up TEXT,
                action_plan TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(person_id) REFERENCES persons(id)
            );
            """
        )
        conn.commit()


def rows(query: str, params: Iterable | tuple = ()) -> list[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return list(conn.execute(query, params).fetchall())


def execute(sql: str, params: Iterable | tuple = ()) -> None:
    with closing(get_conn()) as conn:
        conn.execute(sql, params)
        conn.commit()


def get_people() -> list[sqlite3.Row]:
    return rows("SELECT * FROM persons ORDER BY id DESC")


def person_options() -> dict[str, int]:
    people = get_people()
    return {f"#{p['id']} {p['name']}": p["id"] for p in people}


def save_upload(person_id: int, uploaded_file) -> tuple[str, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = uploaded_file.name.replace("/", "_")
    person_dir = UPLOAD_DIR / f"person_{person_id}"
    person_dir.mkdir(parents=True, exist_ok=True)
    output = person_dir / f"{ts}_{safe_name}"
    output.write_bytes(uploaded_file.getbuffer())
    return str(output), uploaded_file.name


def section_people() -> None:
    st.subheader("1) 人员档案")
    with st.form("person_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("姓名*")
        gender = c2.selectbox("性别", ["", "男", "女", "其他"])
        birth_date = c3.date_input("出生日期", value=None)
        phone = st.text_input("联系电话")
        relation = st.text_input("家庭关系（如：本人/父亲/母亲）")
        notes = st.text_area("备注")
        if st.form_submit_button("保存档案"):
            if not name.strip():
                st.error("姓名为必填项")
            else:
                execute(
                    "INSERT INTO persons(name, gender, birth_date, phone, relation, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        name.strip(),
                        gender,
                        str(birth_date) if birth_date else None,
                        phone.strip(),
                        relation.strip(),
                        notes.strip(),
                    ),
                )
                st.success("人员档案已保存")

    st.dataframe(get_people(), use_container_width=True)


def section_reports() -> None:
    st.subheader("2) 报告上传")
    opts = person_options()
    if not opts:
        st.info("请先在“人员档案”中添加家庭成员。")
        return

    with st.form("report_form", clear_on_submit=True):
        person_label = st.selectbox("选择人员", list(opts.keys()))
        report_date = st.date_input("报告日期", value=datetime.today())
        report_type = st.selectbox("报告类型", ["检验", "影像", "门诊", "体检", "其他"])
        title = st.text_input("报告标题")
        source = st.text_input("来源机构")
        notes = st.text_area("备注")
        uploaded = st.file_uploader("上传文件", type=None)
        if st.form_submit_button("上传并登记"):
            if uploaded is None:
                st.error("请先选择文件")
            else:
                person_id = opts[person_label]
                fp, fn = save_upload(person_id, uploaded)
                execute(
                    """INSERT INTO reports(person_id, report_date, report_type, title, file_path, file_name, source, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (person_id, str(report_date), report_type, title.strip(), fp, fn, source.strip(), notes.strip()),
                )
                st.success(f"文件已保存到本地：{fp}")


def section_report_library() -> None:
    st.subheader("3) 报告库")
    data = rows(
        """SELECT r.*, p.name AS person_name FROM reports r
        JOIN persons p ON p.id=r.person_id ORDER BY r.report_date DESC, r.id DESC"""
    )
    st.dataframe(data, use_container_width=True)


def section_manual_entries() -> None:
    st.subheader("4) 手动录入")
    opts = person_options()
    if not opts:
        st.info("请先添加人员档案。")
        return
    with st.form("manual_form", clear_on_submit=True):
        person_label = st.selectbox("人员", list(opts.keys()), key="manual_person")
        entry_date = st.date_input("日期", value=datetime.today(), key="manual_date")
        category = st.selectbox("类别", ["检验指标", "影像发现", "门诊意见"])
        item_name = st.text_input("项目/部位")
        value_text = st.text_input("指标值/描述")
        conclusion = st.text_area("结论")
        notes = st.text_area("补充说明")
        if st.form_submit_button("保存录入"):
            execute(
                """INSERT INTO manual_entries(person_id, entry_date, category, item_name, value_text, conclusion, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (opts[person_label], str(entry_date), category, item_name.strip(), value_text.strip(), conclusion.strip(), notes.strip()),
            )
            st.success("已保存手动录入")

    all_entries = rows(
        """SELECT m.*, p.name AS person_name FROM manual_entries m
        JOIN persons p ON p.id=m.person_id ORDER BY m.entry_date DESC, m.id DESC"""
    )
    st.dataframe(all_entries, use_container_width=True)


def section_issues() -> None:
    st.subheader("5) 健康问题追踪")
    opts = person_options()
    if not opts:
        st.info("请先添加人员档案。")
        return
    with st.form("issue_form", clear_on_submit=True):
        person_label = st.selectbox("人员", list(opts.keys()), key="issue_person")
        issue_name = st.text_input("问题名称")
        severity = st.selectbox("严重程度", ["低", "中", "高"])
        status = st.selectbox("状态", ["待跟进", "跟进中", "稳定", "已关闭"])
        start_date = st.date_input("开始日期", value=datetime.today(), key="issue_start")
        next_follow_up = st.date_input("下次复查", value=datetime.today(), key="issue_next")
        action_plan = st.text_area("行动计划")
        notes = st.text_area("备注", key="issue_notes")
        if st.form_submit_button("保存追踪"):
            if not issue_name.strip():
                st.error("问题名称不能为空")
            else:
                execute(
                    """INSERT INTO health_issues(person_id, issue_name, severity, status, start_date, next_follow_up, action_plan, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (opts[person_label], issue_name.strip(), severity, status, str(start_date), str(next_follow_up), action_plan.strip(), notes.strip()),
                )
                st.success("已保存健康问题")

    issues = rows(
        """SELECT h.*, p.name AS person_name FROM health_issues h
        JOIN persons p ON p.id=h.person_id ORDER BY h.next_follow_up ASC"""
    )
    st.dataframe(issues, use_container_width=True)


def section_timeline() -> None:
    st.subheader("6) 时间轴")
    events = rows(
        """
        SELECT entry_date AS event_date, '手动录入' AS event_type, category || ' - ' || COALESCE(item_name, '') AS event_title,
               conclusion AS details FROM manual_entries
        UNION ALL
        SELECT report_date, '报告上传', COALESCE(title, report_type), COALESCE(file_name, '') FROM reports
        UNION ALL
        SELECT start_date, '健康问题', issue_name, status || ' / 下次复查: ' || COALESCE(next_follow_up, '') FROM health_issues
        ORDER BY event_date DESC
        """
    )
    st.dataframe(events, use_container_width=True)


def section_doctor_template() -> None:
    st.subheader("7) 医生摘要模板")
    template = """【就诊摘要模板】
1. 基本信息：姓名/年龄/主要诉求
2. 近期异常：
   - 检验指标：
   - 影像发现：
   - 门诊意见：
3. 既往史与用药：
4. 当前健康问题追踪：
5. 需要医生重点解答的问题：
   - 
   - 
6. 下步复查计划（拟）：
"""
    st.text_area("可复制给医生", value=template, height=280)


def main() -> None:
    st.set_page_config(page_title="家庭健康档案工具 v1", layout="wide")
    init_db()
    st.title("家庭健康档案工具 v1")
    st.caption("技术栈：Streamlit + SQLite + 本地文件存储（纯本地，不调用外部 API，不上传云端）")

    tabs = st.tabs(["人员档案", "报告上传", "报告库", "手动录入", "健康问题追踪", "时间轴", "医生摘要模板"])
    with tabs[0]:
        section_people()
    with tabs[1]:
        section_reports()
    with tabs[2]:
        section_report_library()
    with tabs[3]:
        section_manual_entries()
    with tabs[4]:
        section_issues()
    with tabs[5]:
        section_timeline()
    with tabs[6]:
        section_doctor_template()

    st.markdown("---")
    st.caption("医疗免责声明：本工具仅用于健康资料整理，不提供医学诊断，不替代医生面诊。")


if __name__ == "__main__":
    main()
