from __future__ import annotations

from .geometry import distance
from .models import WidthSample


class CrackWidthGauge:
    """宽度卡尺：通过裂缝两侧两个点计算宽度。"""

    @staticmethod
    def make_sample(p1, p2, meter_per_pixel):
        pixel_width = distance(p1, p2)
        if meter_per_pixel:
            width_mm = pixel_width * meter_per_pixel * 1000
        else:
            width_mm = pixel_width
        return WidthSample(p1=p1, p2=p2, width_mm=width_mm)

    @staticmethod
    def status_text(width_mm: float) -> str:
        if width_mm <= 0:
            return "未采样"
        if width_mm < 2:
            return "细微裂缝"
        if width_mm < 5:
            return "明显裂缝"
        if width_mm < 8:
            return "较宽裂缝"
        return "宽度超限，建议复核"
