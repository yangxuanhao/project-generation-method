from datetime import datetime, timedelta
from app.core.database import fetch_all, fetch_one, execute, log_action


def list_reworks(project_id: int | None = None) -> list[dict]:
    if project_id:
        return fetch_all("""SELECT r.*, s.sample_code, s.filename FROM rework_tasks r LEFT JOIN samples s ON r.sample_id=s.id WHERE r.project_id=? ORDER BY r.id DESC""", (project_id,))
    return fetch_all("SELECT * FROM rework_tasks ORDER BY id DESC")


def create_rework(sample_id: int, reviewer: str, issue_type: str, issue_desc: str, requirement: str) -> int:
    sample = fetch_one("SELECT * FROM samples WHERE id=?", (sample_id,))
    code = f"RW-{datetime.now().strftime('%Y%m%d%H%M%S')}-{sample_id}"
    rid = execute("""INSERT INTO rework_tasks(rework_code,sample_id,project_id,labeler,reviewer,issue_type,issue_desc,requirement,deadline,status)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""", (code, sample_id, sample['project_id'], sample.get('assigned_to') or 'labeler', reviewer, issue_type, issue_desc, requirement, (datetime.now()+timedelta(days=3)).strftime('%Y-%m-%d'), '待返工'))
    execute("UPDATE samples SET status='返工中', rework_count=rework_count+1 WHERE id=?", (sample_id,))
    log_action(reviewer, '生成返工任务', f"{code} {issue_type}")
    return rid


def update_rework_status(rework_id: int, status: str, username: str, note: str = '') -> None:
    execute("UPDATE rework_tasks SET status=?, second_review=? WHERE id=?", (status, note, rework_id))
    log_action(username, '更新返工状态', f"返工单{rework_id} -> {status} {note}")
