from __future__ import annotations


class AnnotationQualityChecker:
    """标注质量评分：用于检查比例尺、宽度采样、复核状态、漏标候选等问题。"""

    @staticmethod
    def score(task):
        score = 100
        details = []
        if not task:
            return 0, ["未创建标注任务"]
        if not task.meter_per_pixel:
            score -= 20
            details.append("未完成比例尺标定，扣20分")
        if not task.cracks and not task.regions:
            score -= 25
            details.append("当前影像没有正式裂缝或网裂区域，扣25分")
        for crack in task.cracks:
            if len(crack.points) < 2:
                score -= 5
                details.append(f"{crack.crack_id} 节点不足，扣5分")
            if crack.crack_type in ["", "待判定", "未分类"]:
                score -= 5
                details.append(f"{crack.crack_id} 类型未确认，扣5分")
            if not crack.width_samples:
                score -= 4
                details.append(f"{crack.crack_id} 未进行宽度采样，扣4分")
            if crack.review_status not in ["已通过", "已锁定"]:
                score -= 3
                details.append(f"{crack.crack_id} 未复核通过，扣3分")
        active_candidates = [c for c in task.candidates if c.status == "待确认"]
        if active_candidates:
            score -= min(15, len(active_candidates) * 3)
            details.append(f"仍有 {len(active_candidates)} 条疑似漏标候选未处理")
        score = max(0, min(100, int(score)))
        if not details:
            details.append("标注完整性较好，可进入成果导出")
        return score, details
