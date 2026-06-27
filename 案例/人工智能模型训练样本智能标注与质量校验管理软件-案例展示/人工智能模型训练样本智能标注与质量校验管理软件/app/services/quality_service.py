from app.core.database import fetch_all, fetch_one, execute, log_action
from app.algorithms.bbox_quality import check_bbox, check_duplicate_boxes
from app.algorithms.text_quality import check_text_sample, similarity


def clear_open_issues(sample_id: int) -> None:
    execute("UPDATE quality_issues SET status='已关闭' WHERE sample_id=? AND status!='已关闭'", (sample_id,))


def run_quality_check(sample_id: int, username: str = 'system') -> list[dict]:
    sample = fetch_one("SELECT * FROM samples WHERE id=?", (sample_id,))
    if not sample:
        return []
    clear_open_issues(sample_id)
    issues = []
    if sample['sample_type'] == 'image':
        annotations = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND status!='已删除'", (sample_id,))
        if not annotations:
            issues.append({'type': '当前图片无任何标签', 'severity': '高', 'rule': 'EmptyAnnotation', 'position': '全图', 'suggestion': '确认是否空图像，非空图像需补充目标标注。', 'annotation_id': None})
        for ann in annotations:
            for issue in check_bbox(ann, sample['width'], sample['height']):
                issue['annotation_id'] = ann['id']
                issues.append(issue)
            if ann['source'] == '预标注' and ann['status'] == '待确认':
                issues.append({'type': '预标注目标未处理', 'severity': '中', 'rule': 'UnconfirmedPrelabel', 'position': f"对象{ann['id']}", 'suggestion': '接受、修改或删除该预标注候选框。', 'annotation_id': ann['id']})
        issues.extend(check_duplicate_boxes(annotations))
    else:
        annotations = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND status!='已删除'", (sample_id,))
        labels = [a['label'] for a in annotations if a['label']]
        reason = annotations[0]['comment'] if annotations else ''
        issues.extend([{**x, 'annotation_id': annotations[0]['id'] if annotations else None} for x in check_text_sample(sample['text_content'], labels, reason)])
        # same project duplicate/inconsistent labels
        peers = fetch_all("SELECT s.id,s.text_content,a.label FROM samples s LEFT JOIN annotations a ON a.sample_id=s.id WHERE s.project_id=? AND s.id!=? AND s.sample_type='text'", (sample['project_id'], sample_id))
        for p in peers:
            if similarity(sample['text_content'] or '', p['text_content'] or '') > 0.92 and labels and p.get('label') and p['label'] not in labels:
                issues.append({'type': '同义文本标签不一致', 'severity': '高', 'rule': 'SimilarTextConflict', 'position': f"与样本{p['id']}相似", 'suggestion': f"复核当前标签 {labels} 与历史标签 {p['label']} 的冲突。", 'annotation_id': None})
                break
    for issue in issues:
        execute("""INSERT INTO quality_issues(sample_id,annotation_id,issue_type,severity,rule_name,position_text,suggestion,status)
                   VALUES(?,?,?,?,?,?,?,?)""", (sample_id, issue.get('annotation_id'), issue['type'], issue['severity'], issue['rule'], issue['position'], issue['suggestion'], '待处理'))
    status = '自动质检异常' if issues else '已保存'
    execute("UPDATE samples SET status=?, qc_status=? WHERE id=?", (status, '待质检', sample_id))
    log_action(username, '执行自动质检', f"样本{sample_id} 检出 {len(issues)} 个问题")
    return issues


def issues_for_project(project_id: int) -> list[dict]:
    return fetch_all("""SELECT qi.*, s.sample_code, s.filename, s.sample_type FROM quality_issues qi
                        JOIN samples s ON qi.sample_id=s.id WHERE s.project_id=? ORDER BY qi.status, qi.severity DESC, qi.id DESC""", (project_id,))


def submit_for_review(sample_ids: list[int], username: str) -> tuple[bool, str]:
    total_issues = 0
    for sid in sample_ids:
        issues = run_quality_check(sid, username)
        total_issues += len([i for i in issues if i['severity'] in ('高', '中')])
    if total_issues:
        return False, f"仍有 {total_issues} 个中高风险问题未处理，不能提交审核。"
    for sid in sample_ids:
        execute("UPDATE samples SET status='已提交', qc_status='待质检' WHERE id=?", (sid,))
    log_action(username, '提交审核', f"提交 {len(sample_ids)} 个样本，强制检查通过")
    return True, f"当前任务包共 {len(sample_ids)} 个样本，自动质检通过，可提交审核。"


def reviewer_decision(sample_id: int, passed: bool, username: str, comment: str) -> None:
    execute("UPDATE samples SET qc_status=?, status=? WHERE id=?", ('已通过' if passed else '退回返工', '已通过' if passed else '返工中', sample_id))
    log_action(username, '人工质检结论', f"样本{sample_id} {'通过' if passed else '退回'}：{comment}")
