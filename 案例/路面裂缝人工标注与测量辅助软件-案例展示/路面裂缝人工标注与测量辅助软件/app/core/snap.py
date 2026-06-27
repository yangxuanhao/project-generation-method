from __future__ import annotations

from typing import Tuple, Optional

Point = Tuple[float, float]


class CrackSnapAssistant:
    """磁吸辅助：在点击点周围搜索更暗的像素，使人工点位靠近裂缝暗线。"""

    def __init__(self, enabled: bool = False, radius: int = 10):
        self.enabled = enabled
        self.radius = radius
        self.last_message = "磁吸未启用"

    def set_enabled(self, value: bool):
        self.enabled = value
        self.last_message = "磁吸辅助已开启" if value else "磁吸辅助已关闭"

    def set_radius(self, radius: int):
        self.radius = max(2, min(int(radius), 40))
        self.last_message = f"磁吸半径已调整为 {self.radius} 像素"

    def snap_qimage(self, qimage, x: float, y: float) -> Point:
        if not self.enabled or qimage is None or qimage.isNull():
            return (x, y)
        width, height = qimage.width(), qimage.height()
        cx, cy = int(round(x)), int(round(y))
        best = (cx, cy)
        best_score = 999999
        r = self.radius
        for yy in range(max(0, cy - r), min(height, cy + r + 1)):
            for xx in range(max(0, cx - r), min(width, cx + r + 1)):
                color = qimage.pixelColor(xx, yy)
                gray = (color.red() * 30 + color.green() * 59 + color.blue() * 11) / 100
                # 越暗越可能是裂缝，同时距离点击点不能太远
                dist_penalty = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5 * 2.2
                score = gray + dist_penalty
                if score < best_score:
                    best_score = score
                    best = (xx, yy)
        if abs(best[0] - cx) + abs(best[1] - cy) > 0:
            self.last_message = f"点位已磁吸：({cx},{cy}) → ({best[0]},{best[1]})"
        return float(best[0]), float(best[1])
