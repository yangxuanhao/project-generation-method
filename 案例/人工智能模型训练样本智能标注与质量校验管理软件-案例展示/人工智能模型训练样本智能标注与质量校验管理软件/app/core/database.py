import sqlite3
from contextlib import contextmanager
from typing import Iterable, Any
from app.core.config import DB_PATH, DATA_DIR

SCHEMA = r"""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    project_type TEXT,
    data_type TEXT,
    task_type TEXT,
    training_goal TEXT,
    owner TEXT,
    reviewer TEXT,
    status TEXT,
    deadline TEXT,
    version_no TEXT,
    sample_count INTEGER DEFAULT 0,
    label_count INTEGER DEFAULT 0,
    health_score REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    sample_code TEXT,
    sample_type TEXT,
    filename TEXT,
    file_path TEXT,
    text_content TEXT,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    status TEXT DEFAULT '未开始',
    risk_tags TEXT DEFAULT '',
    is_ground_truth INTEGER DEFAULT 0,
    is_duplicate INTEGER DEFAULT 0,
    is_low_confidence INTEGER DEFAULT 0,
    rework_count INTEGER DEFAULT 0,
    assigned_to TEXT,
    qc_status TEXT DEFAULT '未质检',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES dataset_projects(id)
);

CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    name TEXT,
    code TEXT,
    color TEXT,
    label_type TEXT,
    shortcut TEXT,
    required INTEGER DEFAULT 0,
    exclusive INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    description TEXT,
    positive_example TEXT,
    negative_example TEXT,
    note TEXT,
    FOREIGN KEY(project_id) REFERENCES dataset_projects(id)
);

CREATE TABLE IF NOT EXISTS annotation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    rule_type TEXT,
    title TEXT,
    content TEXT,
    severity TEXT DEFAULT '中',
    enabled INTEGER DEFAULT 1,
    FOREIGN KEY(project_id) REFERENCES dataset_projects(id)
);

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    label TEXT,
    annotation_type TEXT DEFAULT 'bbox',
    x REAL DEFAULT 0,
    y REAL DEFAULT 0,
    w REAL DEFAULT 0,
    h REAL DEFAULT 0,
    entity_start INTEGER DEFAULT 0,
    entity_end INTEGER DEFAULT 0,
    entity_text TEXT DEFAULT '',
    confidence REAL DEFAULT 1,
    source TEXT DEFAULT '人工',
    status TEXT DEFAULT '已确认',
    created_by TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sample_id) REFERENCES samples(id)
);

CREATE TABLE IF NOT EXISTS quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    annotation_id INTEGER,
    issue_type TEXT,
    severity TEXT,
    rule_name TEXT,
    position_text TEXT,
    suggestion TEXT,
    status TEXT DEFAULT '待处理',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sample_id) REFERENCES samples(id)
);

CREATE TABLE IF NOT EXISTS consensus_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    sample_id INTEGER,
    worker_a TEXT,
    worker_b TEXT,
    iou_score REAL,
    label_agreement REAL,
    diff_summary TEXT,
    need_arbitration INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ground_truth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER,
    answer_json TEXT,
    score REAL DEFAULT 100,
    conclusion TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rework_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rework_code TEXT UNIQUE,
    sample_id INTEGER,
    project_id INTEGER,
    labeler TEXT,
    reviewer TEXT,
    issue_type TEXT,
    issue_desc TEXT,
    requirement TEXT,
    deadline TEXT,
    status TEXT DEFAULT '待返工',
    second_review TEXT DEFAULT '',
    arbitration_result TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    version_no TEXT,
    sample_total INTEGER,
    passed_total INTEGER,
    qc_pass_rate REAL,
    train_ratio REAL,
    val_ratio REAL,
    test_ratio REAL,
    status TEXT,
    frozen_by TEXT,
    frozen_at TEXT,
    description TEXT,
    diff_from_prev TEXT
);

CREATE TABLE IF NOT EXISTS export_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    format TEXT,
    output_path TEXT,
    check_result TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    report_type TEXT,
    title TEXT,
    file_path TEXT,
    conclusion TEXT,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action TEXT,
    detail TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def fetch_all(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def fetch_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        row = cur.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(params))
        return int(cur.lastrowid)


def execute_many(sql: str, values: list[Iterable[Any]]) -> None:
    with get_conn() as conn:
        conn.executemany(sql, [tuple(v) for v in values])


def log_action(username: str, action: str, detail: str) -> None:
    execute("INSERT INTO operation_logs(username, action, detail) VALUES(?,?,?)", (username, action, detail))
