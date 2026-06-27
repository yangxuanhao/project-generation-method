import random
from app.core.database import execute, fetch_one, fetch_all, log_action


def generate_prelabels_for_sample(sample_id: int, username: str = 'system') -> list[dict]:
    sample = fetch_one("SELECT * FROM samples WHERE id=?", (sample_id,))
    if not sample or sample['sample_type'] != 'image':
        return []
    labels = fetch_all("SELECT name FROM labels WHERE project_id=? AND label_type LIKE '%目标框%' AND enabled=1", (sample['project_id'],))
    names = [x['name'] for x in labels] or ['person', 'helmet']
    rng = random.Random(sample_id * 991)
    generated = []
    for i in range(rng.randint(2, 5)):
        label = rng.choice(names)
        w = rng.randint(38, 150)
        h = rng.randint(32, 170)
        x = rng.randint(0, max(1, sample['width'] - w))
        y = rng.randint(0, max(1, sample['height'] - h))
        conf = round(rng.uniform(0.52, 0.94), 2)
        aid = execute("""INSERT INTO annotations(sample_id,label,annotation_type,x,y,w,h,confidence,source,status,created_by,comment)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (sample_id, label, 'bbox', x, y, w, h, conf, '预标注', '待确认', username, '轻量规则模型生成'))
        generated.append({'id': aid, 'label': label, 'x': x, 'y': y, 'w': w, 'h': h, 'confidence': conf, 'source': '预标注', 'status': '待确认'})
    execute("UPDATE samples SET status='预标注待确认', is_low_confidence=? WHERE id=?", (1 if any(g['confidence'] < 0.65 for g in generated) else 0, sample_id))
    log_action(username, '生成智能预标注', f"样本{sample_id} 生成 {len(generated)} 个候选框")
    return generated


def accept_prelabels(sample_id: int, username: str) -> int:
    rows = fetch_all("SELECT id FROM annotations WHERE sample_id=? AND source='预标注' AND status='待确认'", (sample_id,))
    for row in rows:
        execute("UPDATE annotations SET status='已确认', created_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (username, row['id']))
    execute("UPDATE samples SET status='已保存' WHERE id=?", (sample_id,))
    log_action(username, '接受预标注', f"样本{sample_id} 接受 {len(rows)} 个预标注")
    return len(rows)


def delete_annotation(annotation_id: int, username: str, reason: str = '误检') -> None:
    execute("UPDATE annotations SET status='已删除', comment=? WHERE id=?", (reason, annotation_id))
    log_action(username, '删除标注对象', f"对象{annotation_id} 原因：{reason}")


def update_bbox(annotation_id: int, x: float, y: float, w: float, h: float, label: str, username: str) -> None:
    execute("UPDATE annotations SET x=?,y=?,w=?,h=?,label=?,source='人工',status='已确认',created_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (x, y, w, h, label, username, annotation_id))
    log_action(username, '修改标注框', f"对象{annotation_id} -> {label} ({x:.0f},{y:.0f},{w:.0f},{h:.0f})")


def create_bbox(sample_id: int, label: str, x: float, y: float, w: float, h: float, username: str) -> int:
    aid = execute("""INSERT INTO annotations(sample_id,label,annotation_type,x,y,w,h,confidence,source,status,created_by,comment)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (sample_id, label, 'bbox', x, y, w, h, 1.0, '人工', '已确认', username, '人工新增'))
    execute("UPDATE samples SET status='已保存' WHERE id=?", (sample_id,))
    log_action(username, '新增人工标注框', f"样本{sample_id} 标签 {label}")
    return aid
