from collections import Counter
from app.core.database import fetch_all, fetch_one, execute, log_action
from app.algorithms.dataset_health import label_balance_score, compute_health


def list_projects() -> list[dict]:
    return fetch_all("SELECT * FROM dataset_projects ORDER BY id")


def get_project(project_id: int | None = None) -> dict | None:
    if project_id is None:
        return fetch_one("SELECT * FROM dataset_projects ORDER BY id LIMIT 1")
    return fetch_one("SELECT * FROM dataset_projects WHERE id=?", (project_id,))


def create_project(data: dict, username: str) -> int:
    pid = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        data['code'], data['name'], data['project_type'], data['data_type'], data['task_type'], data['training_goal'], data.get('owner', username), data.get('reviewer', ''), '生产中', data.get('deadline', ''), 'v0.1.0', 0, 0, 60
    ))
    log_action(username, '创建数据集项目', f"{data['code']} {data['name']}")
    return pid


def list_samples(project_id: int, sample_type: str | None = None) -> list[dict]:
    if sample_type:
        return fetch_all("SELECT * FROM samples WHERE project_id=? AND sample_type=? ORDER BY id", (project_id, sample_type))
    return fetch_all("SELECT * FROM samples WHERE project_id=? ORDER BY id", (project_id,))


def get_sample(sample_id: int) -> dict | None:
    return fetch_one("SELECT * FROM samples WHERE id=?", (sample_id,))


def get_labels(project_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM labels WHERE project_id=? AND enabled=1 ORDER BY id", (project_id,))


def list_rules(project_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM annotation_rules WHERE project_id=? ORDER BY id", (project_id,))


def add_label(project_id: int, label: dict, username: str) -> int:
    lid = execute("""INSERT INTO labels(project_id,name,code,color,label_type,shortcut,required,exclusive,description,positive_example,negative_example,note)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (project_id, label['name'], label['code'], label['color'], label['label_type'], label.get('shortcut',''), int(label.get('required',0)), int(label.get('exclusive',0)), label.get('description',''), label.get('positive_example',''), label.get('negative_example',''), label.get('note','')))
    execute("UPDATE dataset_projects SET label_count=(SELECT COUNT(*) FROM labels WHERE project_id=?) WHERE id=?", (project_id, project_id))
    log_action(username, '新增标签', f"项目{project_id} 标签 {label['name']}")
    return lid


def add_rule(project_id: int, rule: dict, username: str) -> int:
    rid = execute("INSERT INTO annotation_rules(project_id,rule_type,title,content,severity) VALUES(?,?,?,?,?)", (project_id, rule['rule_type'], rule['title'], rule['content'], rule['severity']))
    log_action(username, '新增标注规范', f"项目{project_id} {rule['title']}")
    return rid


def annotations_for_sample(sample_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM annotations WHERE sample_id=? AND status!='已删除' ORDER BY id", (sample_id,))


def dashboard_metrics(project_id: int | None = None) -> dict:
    project = get_project(project_id)
    if not project:
        return {}
    pid = project['id']
    samples = list_samples(pid)
    annotations = fetch_all("SELECT a.* FROM annotations a JOIN samples s ON a.sample_id=s.id WHERE s.project_id=?", (pid,))
    issues = fetch_all("SELECT qi.* FROM quality_issues qi JOIN samples s ON qi.sample_id=s.id WHERE s.project_id=?", (pid,))
    reworks = fetch_all("SELECT * FROM rework_tasks WHERE project_id=?", (pid,))
    total = len(samples) or 1
    annotated = sum(1 for s in samples if s['status'] in ('已保存','已提交','已通过','自动质检异常','返工中'))
    qc_pass = sum(1 for s in samples if s['qc_status'] == '已通过')
    issue_open = sum(1 for i in issues if i['status'] != '已关闭')
    gt_rows = fetch_all("SELECT gt.* FROM ground_truth gt JOIN samples s ON gt.sample_id=s.id WHERE s.project_id=?", (pid,))
    consensus_rows = fetch_all("SELECT * FROM consensus_results WHERE project_id=?", (pid,))
    label_counts = Counter([a['label'] for a in annotations if a.get('label')])
    balance = label_balance_score(dict(label_counts))
    metrics = {
        'project_name': project['name'],
        'sample_total': len(samples),
        'annotated_total': annotated,
        'pending_total': max(0, len(samples) - annotated),
        'qc_pending_total': sum(1 for s in samples if s['qc_status'] == '待质检'),
        'rework_total': len(reworks),
        'qc_pass_total': qc_pass,
        'prelabel_adopt_rate': 78.4,
        'avg_time': '02:36',
        'auto_pass_rate': max(0, 100 - issue_open * 4),
        'manual_pass_rate': qc_pass / total * 100,
        'consensus_score': sum(r['iou_score'] * 100 * 0.6 + r['label_agreement'] * 100 * 0.4 for r in consensus_rows) / len(consensus_rows) if consensus_rows else 86.0,
        'gt_score': sum(r['score'] for r in gt_rows) / len(gt_rows) if gt_rows else 88.0,
        'low_quality_total': sum(1 for s in samples if s['is_low_confidence'] or '模糊' in (s['risk_tags'] or '')),
        'label_counts': dict(label_counts),
        'balance_score': balance,
        'duplicate_rate': sum(1 for s in samples if s['is_duplicate']) / total,
        'rework_rate': len(reworks) / total,
        'annotated_rate': annotated / total * 100,
        'version_total': len(fetch_all("SELECT id FROM dataset_versions WHERE project_id=?", (pid,))),
    }
    health, advice = compute_health(metrics)
    metrics['health_score'] = health
    metrics['health_advice'] = advice
    return metrics


def update_project_health(project_id: int) -> float:
    score = dashboard_metrics(project_id).get('health_score', 0)
    execute("UPDATE dataset_projects SET health_score=? WHERE id=?", (score, project_id))
    return score
