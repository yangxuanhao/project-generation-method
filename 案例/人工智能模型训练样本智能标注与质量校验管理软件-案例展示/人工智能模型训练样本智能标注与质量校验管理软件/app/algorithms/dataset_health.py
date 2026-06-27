from math import log2


def label_balance_score(label_counts: dict[str, int]) -> float:
    total = sum(label_counts.values())
    if not total or len(label_counts) < 2:
        return 60.0
    probs = [c / total for c in label_counts.values() if c > 0]
    entropy = -sum(p * log2(p) for p in probs)
    max_entropy = log2(len(label_counts))
    return round(100 * entropy / max_entropy, 2) if max_entropy else 60.0


def compute_health(metrics: dict) -> tuple[float, list[str]]:
    complete = metrics.get('annotated_rate', 0)
    auto_pass = metrics.get('auto_pass_rate', 0)
    manual_pass = metrics.get('manual_pass_rate', 0)
    consensus = metrics.get('consensus_score', 0)
    gt = metrics.get('gt_score', 0)
    balance = metrics.get('balance_score', 0)
    duplicate_penalty = metrics.get('duplicate_rate', 0) * 100
    rework_penalty = metrics.get('rework_rate', 0) * 80
    score = complete * 0.20 + auto_pass * 0.15 + manual_pass * 0.15 + consensus * 0.15 + gt * 0.12 + balance * 0.12 + 11
    score = max(0, min(100, score - duplicate_penalty * 0.08 - rework_penalty * 0.10))
    deductions = []
    if complete < 95:
        deductions.append('标注完整度不足，建议优先完成待标注样本。')
    if auto_pass < 90:
        deductions.append('自动质检通过率偏低，需处理越界框、重复框和空标签。')
    if consensus < 85:
        deductions.append('多人一致性不足，建议增加仲裁和规范校准。')
    if balance < 75:
        deductions.append('标签分布不均衡，建议补充少数类样本。')
    if metrics.get('rework_rate', 0) > 0.08:
        deductions.append('返工率偏高，建议复盘高频错误标签。')
    return round(score, 2), deductions
