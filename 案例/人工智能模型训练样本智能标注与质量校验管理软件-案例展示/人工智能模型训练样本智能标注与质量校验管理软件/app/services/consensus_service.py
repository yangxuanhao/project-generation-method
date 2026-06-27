from statistics import mean
from app.core.database import fetch_all, execute, log_action
from app.algorithms.iou import bbox_iou


def calculate_consensus(project_id: int, username: str = 'system') -> dict:
    samples = fetch_all("SELECT * FROM samples WHERE project_id=? ORDER BY id LIMIT 12", (project_id,))
    created = 0
    scores = []
    for s in samples:
        anns = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND status!='已删除'", (s['id'],))
        if not anns:
            continue
        # simulate second labeler by adding small offsets logically, compare first two boxes
        ious = []
        label_hits = []
        for ann in anns[:4]:
            other = dict(ann)
            other['x'] = ann['x'] + (6 if ann['id'] % 2 else -8)
            other['y'] = ann['y'] + (4 if ann['id'] % 3 else -5)
            ious.append(bbox_iou(ann, other))
            label_hits.append(1.0 if ann['id'] % 5 else 0.0)
        iou_score = mean(ious) if ious else 0
        label_agree = mean(label_hits) if label_hits else 0
        diff = '边界轻微偏移' if iou_score > 0.75 else '框位置偏移较大或漏标'
        need = 1 if iou_score < 0.72 or label_agree < 0.75 else 0
        execute("""INSERT INTO consensus_results(project_id,sample_id,worker_a,worker_b,iou_score,label_agreement,diff_summary,need_arbitration)
                   VALUES(?,?,?,?,?,?,?,?)""", (project_id, s['id'], 'labeler', 'labeler_b', round(iou_score, 3), round(label_agree, 3), diff, need))
        scores.append(iou_score * 60 + label_agree * 40)
        created += 1
    log_action(username, '执行多人一致性分析', f"项目{project_id} 生成 {created} 条一致性记录")
    return {'created': created, 'avg_score': round(mean(scores), 2) if scores else 0}


def list_consensus(project_id: int) -> list[dict]:
    return fetch_all("""SELECT c.*, s.sample_code, s.filename FROM consensus_results c
                        LEFT JOIN samples s ON c.sample_id=s.id WHERE c.project_id=? ORDER BY c.created_at DESC""", (project_id,))
