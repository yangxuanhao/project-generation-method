from __future__ import annotations

from typing import List, Tuple
from .geometry import polygon_area_real

Point = Tuple[float, float]


class CrackRegionAnalyzer:
    """网裂区域分析：计算圈选面积和裂缝密度。"""

    @staticmethod
    def area(points: List[Point], meter_per_pixel: float | None) -> float:
        return polygon_area_real(points, meter_per_pixel)

    @staticmethod
    def density(total_length_m: float, area_m2: float) -> float:
        if area_m2 <= 0:
            return 0.0
        return total_length_m / area_m2

    @staticmethod
    def severity(area_m2: float, density: float) -> str:
        score = 0
        if area_m2 > 20:
            score += 2
        elif area_m2 > 5:
            score += 1
        if density > 3:
            score += 2
        elif density > 1:
            score += 1
        if score <= 1:
            return "轻微"
        if score <= 2:
            return "一般"
        if score <= 3:
            return "较重"
        return "严重"
