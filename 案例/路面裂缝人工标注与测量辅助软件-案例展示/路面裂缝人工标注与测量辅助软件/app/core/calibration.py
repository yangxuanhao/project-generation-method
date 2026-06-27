from __future__ import annotations

from typing import Tuple
from .geometry import distance

Point = Tuple[float, float]


class ImageCalibrationEngine:
    """比例尺标定引擎：把像素长度转换为真实道路长度。"""

    @staticmethod
    def calibrate_by_two_points(p1: Point, p2: Point, real_distance_m: float) -> float:
        pixel_distance = distance(p1, p2)
        if pixel_distance <= 0:
            raise ValueError("两个标定点距离过小，无法计算比例尺")
        if real_distance_m <= 0:
            raise ValueError("实际距离必须大于0")
        return real_distance_m / pixel_distance

    @staticmethod
    def describe(meter_per_pixel: float | None) -> str:
        if not meter_per_pixel:
            return "未标定：当前量测结果以像素为单位"
        return f"已标定：1像素约等于 {meter_per_pixel * 1000:.3f} 毫米"

    @staticmethod
    def pixel_to_meter(pixel: float, meter_per_pixel: float | None) -> float:
        return pixel * meter_per_pixel if meter_per_pixel else pixel

    @staticmethod
    def pixel_to_mm(pixel: float, meter_per_pixel: float | None) -> float:
        return pixel * meter_per_pixel * 1000 if meter_per_pixel else pixel
