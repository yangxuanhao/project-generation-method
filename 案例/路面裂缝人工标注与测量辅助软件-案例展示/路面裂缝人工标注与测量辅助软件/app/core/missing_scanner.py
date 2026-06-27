from __future__ import annotations

import math
from typing import List
from .models import CandidateCrack
from .geometry import distance


class MissingCrackScanner:
    """疑似漏标扫描：基于暗像素扫描生成候选裂缝线。演示版不依赖OpenCV。"""

    @staticmethod
    def scan_qimage(qimage, existing_cracks=None, max_candidates: int = 8) -> List[CandidateCrack]:
        existing_cracks = existing_cracks or []
        if qimage is None or qimage.isNull():
            return []
        w, h = qimage.width(), qimage.height()
        step_y = max(12, h // 40)
        step_x = max(10, w // 60)
        raw_segments = []
        for y in range(step_y, h - step_y, step_y):
            dark_run = []
            for x in range(step_x, w - step_x, step_x):
                c = qimage.pixelColor(x, y)
                gray = (c.red() * 30 + c.green() * 59 + c.blue() * 11) / 100
                if gray < 88:
                    dark_run.append((x, y + math.sin(x / 20) * 2))
                else:
                    if len(dark_run) >= 3:
                        raw_segments.append(dark_run)
                    dark_run = []
            if len(dark_run) >= 3:
                raw_segments.append(dark_run)
        candidates = []
        for seg in raw_segments:
            if MissingCrackScanner._covered_by_existing(seg, existing_cracks):
                continue
            score = min(99, 45 + len(seg) * 6)
            candidates.append(CandidateCrack(points=seg, score=score))
            if len(candidates) >= max_candidates:
                break
        return candidates

    @staticmethod
    def _covered_by_existing(points, cracks) -> bool:
        for p in points:
            for crack in cracks:
                for q in crack.points:
                    if distance(p, q) < 20:
                        return True
        return False
