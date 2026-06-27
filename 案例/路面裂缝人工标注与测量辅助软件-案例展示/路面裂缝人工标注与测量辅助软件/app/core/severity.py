from __future__ import annotations

from typing import List, Tuple
from .geometry import bounding_box, polyline_length_real

Point = Tuple[float, float]


class CrackSeverityEvaluator:
    """裂缝诊断：类型建议、严重等级与判定依据。"""

    @staticmethod
    def classify(points: List[Point], is_region: bool = False) -> str:
        if is_region:
            return "网状裂缝"
        if len(points) < 2:
            return "待判定"
        minx, miny, maxx, maxy = bounding_box(points)
        span_x = maxx - minx
        span_y = maxy - miny
        if span_x > span_y * 2:
            return "横向裂缝"
        if span_y > span_x * 2:
            return "纵向裂缝"
        if len(points) >= 6 and (span_x + span_y) > 160:
            return "斜向裂缝"
        return "斜向裂缝"

    @staticmethod
    def evaluate(length_m: float, avg_width_mm: float, max_width_mm: float, crack_type: str) -> tuple[str, List[str]]:
        score = 0
        reasons = []
        if length_m > 5:
            score += 2
            reasons.append("裂缝长度超过5米")
        elif length_m > 2:
            score += 1
            reasons.append("裂缝长度超过2米")
        else:
            reasons.append("裂缝长度较短")
        if avg_width_mm > 5:
            score += 2
            reasons.append("平均宽度超过5毫米")
        elif avg_width_mm > 2:
            score += 1
            reasons.append("平均宽度超过2毫米")
        else:
            reasons.append("平均宽度未超过明显阈值")
        if max_width_mm > 8:
            score += 2
            reasons.append("最大宽度超过8毫米，需重点复核")
        if crack_type in ["网状裂缝", "龟裂", "块状裂缝"]:
            score += 2
            reasons.append("病害类型属于面状或结构风险更高的类型")
        if score <= 1:
            return "轻微", reasons
        if score <= 3:
            return "一般", reasons
        if score <= 5:
            return "较重", reasons
        return "严重", reasons

    @staticmethod
    def refresh_crack(crack, meter_per_pixel: float | None):
        length = polyline_length_real(crack.points, meter_per_pixel)
        # 未标定时长度单位是像素，为了严重等级不夸张，换一个演示折算
        display_length = length if meter_per_pixel else length / 180
        crack.suggestion_type = CrackSeverityEvaluator.classify(crack.points)
        if crack.crack_type in ["待判定", "", "未分类"]:
            crack.crack_type = crack.suggestion_type
        severity, reasons = CrackSeverityEvaluator.evaluate(display_length, crack.avg_width_mm, crack.max_width_mm, crack.crack_type)
        crack.severity = severity
        return reasons
