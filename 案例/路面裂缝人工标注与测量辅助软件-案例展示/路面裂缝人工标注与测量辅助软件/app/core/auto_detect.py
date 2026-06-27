from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import math

import numpy as np
from PIL import Image, ImageFilter

from .models import CrackObject, WidthSample
from .geometry import polyline_length, distance
from .severity import CrackSeverityEvaluator

Point = Tuple[float, float]


class CrackAutoDetector:
    """自动裂缝标注算法。

    本版不再使用“全局暗像素连通”作为主逻辑，而是采用：
    1. 局部背景减法，增强“比周边更暗”的线状裂缝；
    2. 邻域连续性过滤，去掉单个石子、纹理噪点；
    3. 连通域几何筛选，过滤块状污渍、边缘噪声和短小纹理；
    4. 线性支撑度验证，确认拟合折线确实落在暗线区域上；
    5. 默认保守识别，避免一次性生成大量错误标注线。
    """

    PRESETS = {
        "保守": {
            "contrast_percentile": 96.0,
            "min_contrast": 18,
            "min_length_px": 130,
            "min_area": 14,
            "max_count": 6,
            "support": 0.42,
            "edge_guard": 0.035,
            "neighbor_min": 2,
            "line_width": 2,
        },
        "标准": {
            "contrast_percentile": 94.0,
            "min_contrast": 14,
            "min_length_px": 95,
            "min_area": 10,
            "max_count": 8,
            "support": 0.37,
            "edge_guard": 0.025,
            "neighbor_min": 2,
            "line_width": 2,
        },
        "增强": {
            "contrast_percentile": 91.0,
            "min_contrast": 11,
            "min_length_px": 70,
            "min_area": 8,
            "max_count": 12,
            "support": 0.30,
            "edge_guard": 0.018,
            "neighbor_min": 1,
            "line_width": 3,
        },
    }

    @staticmethod
    def detect_from_image(
        image_path: str | Path,
        meter_per_pixel: float | None = None,
        max_cracks: int | None = None,
        min_length_px: float | None = None,
        sensitivity: str = "保守",
    ) -> List[CrackObject]:
        arr = CrackAutoDetector._load_gray(image_path)
        if arr is None:
            return []

        cfg = dict(CrackAutoDetector.PRESETS.get(sensitivity, CrackAutoDetector.PRESETS["保守"]))
        if max_cracks is not None:
            cfg["max_count"] = max_cracks
        if min_length_px is not None:
            cfg["min_length_px"] = min_length_px

        small, scale = CrackAutoDetector._downsample(arr)
        width_contrast = CrackAutoDetector._width_contrast(arr)

        contrast = CrackAutoDetector._local_dark_contrast(small)
        strong_mask = CrackAutoDetector._build_mask(small, contrast, cfg)

        # 只在增强模式下轻微连通裂缝断点；保守/标准不做过度膨胀，避免误检堆叠
        if sensitivity == "增强":
            strong_mask = CrackAutoDetector._dilate(strong_mask)
            strong_mask = CrackAutoDetector._neighbor_filter(strong_mask, min_neighbors=cfg["neighbor_min"])

        comps = CrackAutoDetector._components(strong_mask)
        scored: list[tuple[float, CrackObject, tuple[float, float, float, float]]] = []
        used_boxes: list[tuple[float, float, float, float]] = []

        for comp in sorted(comps, key=len, reverse=True):
            if len(comp) < cfg["min_area"]:
                continue

            pts_small = np.array(comp, dtype=float)
            if not CrackAutoDetector._looks_like_crack(pts_small, strong_mask.shape, cfg):
                continue

            # 还原到原图坐标后拟合折线
            pts = np.array([(x * scale, y * scale) for x, y in comp], dtype=float)
            poly = CrackAutoDetector._fit_polyline(pts)
            if len(poly) < 2:
                continue

            length = polyline_length(poly)
            if length < cfg["min_length_px"]:
                continue

            support = CrackAutoDetector._line_support_score(poly, strong_mask, scale, width=cfg["line_width"])
            if support < cfg["support"]:
                continue

            box = CrackAutoDetector._bbox(poly)
            if CrackAutoDetector._overlaps_existing(box, used_boxes, threshold=0.55):
                continue

            crack = CrackObject(points=poly, source="自动识别")
            CrackAutoDetector._auto_fill_widths_from_contrast(width_contrast, crack, meter_per_pixel)
            CrackSeverityEvaluator.refresh_crack(crack, meter_per_pixel)

            # 综合分：长度、线性支撑度、宽度采样完整度
            width_bonus = len(crack.width_samples) * 15
            score = length * 0.35 + support * 180 + width_bonus
            scored.append((score, crack, box))

        # 按分数取前 N 条，避免画面被误检线条铺满
        scored.sort(key=lambda x: x[0], reverse=True)
        cracks: list[CrackObject] = []
        for _, crack, box in scored:
            if CrackAutoDetector._overlaps_existing(box, used_boxes, threshold=0.42):
                continue
            used_boxes.append(box)
            cracks.append(crack)
            if len(cracks) >= cfg["max_count"]:
                break

        return cracks

    @staticmethod
    def estimate_widths(image_path: str | Path, crack: CrackObject, meter_per_pixel: float | None) -> list[WidthSample]:
        """返回最窄、中间位置、最宽三处宽度。"""
        arr = CrackAutoDetector._load_gray(image_path)
        if arr is None:
            return []
        contrast = CrackAutoDetector._width_contrast(arr)
        samples = CrackAutoDetector._sample_width_profile_from_contrast(contrast, crack.points, meter_per_pixel)
        return CrackAutoDetector._pick_min_mid_max(samples)

    @staticmethod
    def width_summary(samples: list[WidthSample]) -> str:
        if not samples:
            return "尚未估算宽度"
        vals = [s.width_mm for s in samples]
        return f"最窄：{min(vals):.2f}mm｜中间：{vals[len(vals)//2]:.2f}mm｜最宽：{max(vals):.2f}mm"

    @staticmethod
    def _load_gray(image_path: str | Path):
        try:
            img = Image.open(image_path).convert("L")
            return np.array(img)
        except Exception:
            return None

    @staticmethod
    def _downsample(arr: np.ndarray):
        h, w = arr.shape
        scale = max(1, math.ceil(max(h, w) / 980))
        if scale == 1:
            return arr, 1
        hh, ww = h // scale, w // scale
        arr = arr[:hh * scale, :ww * scale]
        small = arr.reshape(hh, scale, ww, scale).mean(axis=(1, 3)).astype(np.uint8)
        return small, scale

    @staticmethod
    def _local_dark_contrast(gray: np.ndarray) -> np.ndarray:
        # 背景半径与图像尺寸相关；半径太小会把路面纹理当裂缝，太大会漏掉细线
        radius = max(7, int(min(gray.shape) / 75))
        bg = np.array(Image.fromarray(gray).filter(ImageFilter.GaussianBlur(radius=radius))).astype(np.int16)
        g = gray.astype(np.int16)
        contrast = bg - g
        contrast[contrast < 0] = 0
        return contrast.astype(np.uint8)

    @staticmethod
    def _build_mask(gray: np.ndarray, contrast: np.ndarray, cfg: dict) -> np.ndarray:
        c_thr = max(cfg["min_contrast"], int(np.percentile(contrast, cfg["contrast_percentile"])))
        dark_cap = int(np.percentile(gray, 70))
        mask = (contrast >= c_thr) & (gray <= dark_cap)

        # 去掉孤立噪点：裂缝应当至少有少量相邻暗线像素
        mask = CrackAutoDetector._neighbor_filter(mask, min_neighbors=cfg["neighbor_min"])

        # 细化边缘保护：去掉图像最边缘的孤立脏边
        h, w = mask.shape
        margin_y = max(2, int(h * cfg["edge_guard"]))
        margin_x = max(2, int(w * cfg["edge_guard"]))
        mask[:margin_y, :] = False
        mask[-margin_y:, :] = False
        mask[:, :margin_x] = False
        mask[:, -margin_x:] = False
        return mask

    @staticmethod
    def _neighbor_filter(mask: np.ndarray, min_neighbors: int = 2) -> np.ndarray:
        padded = np.pad(mask, 1, mode="constant", constant_values=False)
        count = np.zeros_like(mask, dtype=np.uint8)
        for dy in range(3):
            for dx in range(3):
                if dy == 1 and dx == 1:
                    continue
                count += padded[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
        return mask & (count >= min_neighbors)

    @staticmethod
    def _dilate(mask: np.ndarray) -> np.ndarray:
        out = mask.copy()
        padded = np.pad(mask, 1, mode="constant", constant_values=False)
        for dy in range(3):
            for dx in range(3):
                out |= padded[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
        return out

    @staticmethod
    def _components(mask: np.ndarray):
        h, w = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        comps = []
        for y in range(h):
            for x in range(w):
                if not mask[y, x] or visited[y, x]:
                    continue
                stack = [(x, y)]
                visited[y, x] = True
                comp = []
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for nx in (cx - 1, cx, cx + 1):
                        for ny in (cy - 1, cy, cy + 1):
                            if nx < 0 or ny < 0 or nx >= w or ny >= h:
                                continue
                            if visited[ny, nx] or not mask[ny, nx]:
                                continue
                            visited[ny, nx] = True
                            stack.append((nx, ny))
                comps.append(comp)
        return comps

    @staticmethod
    def _looks_like_crack(points_small: np.ndarray, shape, cfg: dict) -> bool:
        if len(points_small) < cfg["min_area"]:
            return False
        h, w = shape
        xs = points_small[:, 0]
        ys = points_small[:, 1]
        minx, maxx = float(xs.min()), float(xs.max())
        miny, maxy = float(ys.min()), float(ys.max())
        span_x = maxx - minx + 1
        span_y = maxy - miny + 1
        major_span = max(span_x, span_y)
        minor_span = min(span_x, span_y)
        area = float(len(points_small))
        bbox_area = max(1.0, span_x * span_y)
        fill_ratio = area / bbox_area

        if major_span < max(18, cfg["min_length_px"] / 5):
            return False

        # 块状污渍/水泥颗粒常表现为填充率较高，裂缝通常填充率较低
        if fill_ratio > 0.42 and area > 35:
            return False

        center = points_small.mean(axis=0)
        shifted = points_small - center
        cov = np.cov(shifted.T)
        vals, _ = np.linalg.eigh(cov)
        vals = np.sort(vals)[::-1]
        if vals[0] <= 1e-6:
            return False
        slenderness = vals[0] / max(vals[1], 1e-6)

        # 允许弯曲裂缝，但不能像一团噪点
        if slenderness < 1.8 and minor_span > major_span * 0.65 and area > 45:
            return False

        # 边缘短小碎线过滤
        edge_band_x = w * 0.06
        edge_band_y = h * 0.06
        near_edge = minx < edge_band_x or maxx > w - edge_band_x or miny < edge_band_y or maxy > h - edge_band_y
        if near_edge and major_span < max(36, min(w, h) * 0.08):
            return False

        return True

    @staticmethod
    def _fit_polyline(points: np.ndarray) -> List[Point]:
        if len(points) < 2:
            return []
        center = points.mean(axis=0)
        shifted = points - center
        cov = np.cov(shifted.T)
        vals, vecs = np.linalg.eigh(cov)
        order = np.argsort(vals)[::-1]
        vecs = vecs[:, order]
        major = vecs[:, 0]
        proj_major = shifted @ major
        major_span = proj_major.max() - proj_major.min()
        if major_span < 20:
            return []

        # 多分箱能更贴合弯曲线，但避免太密导致标签挤成一团
        bin_count = 6 if major_span < 160 else 8
        bins = np.linspace(proj_major.min(), proj_major.max(), bin_count)
        result = []
        for i in range(len(bins) - 1):
            mask = (proj_major >= bins[i]) & (proj_major <= bins[i + 1])
            sel = points[mask]
            if len(sel) == 0:
                continue
            x, y = np.median(sel[:, 0]), np.median(sel[:, 1])
            if not result or distance(result[-1], (float(x), float(y))) > 12:
                result.append((float(x), float(y)))

        if len(result) < 2:
            a = center + major * proj_major.min()
            b = center + major * proj_major.max()
            result = [(float(a[0]), float(a[1])), (float(b[0]), float(b[1]))]
        return result

    @staticmethod
    def _line_support_score(poly: list[Point], mask_small: np.ndarray, scale: int, width: int = 2) -> float:
        h, w = mask_small.shape
        hit = 0
        total = 0
        for a, b in zip(poly[:-1], poly[1:]):
            ax, ay = a[0] / scale, a[1] / scale
            bx, by = b[0] / scale, b[1] / scale
            seg_len = max(1, int(math.hypot(bx - ax, by - ay)))
            steps = max(8, min(80, seg_len))
            for i in range(steps + 1):
                t = i / steps
                x = int(round(ax + (bx - ax) * t))
                y = int(round(ay + (by - ay) * t))
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                total += 1
                x1, x2 = max(0, x - width), min(w, x + width + 1)
                y1, y2 = max(0, y - width), min(h, y + width + 1)
                if mask_small[y1:y2, x1:x2].any():
                    hit += 1
        return hit / max(1, total)

    @staticmethod
    def _width_contrast(arr: np.ndarray) -> np.ndarray:
        radius = max(5, int(min(arr.shape) / 90))
        bg = np.array(Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=radius))).astype(np.int16)
        gray = arr.astype(np.int16)
        contrast = bg - gray
        contrast[contrast < 0] = 0
        return contrast.astype(np.uint8)

    @staticmethod
    def _auto_fill_widths_from_contrast(contrast: np.ndarray, crack: CrackObject, meter_per_pixel: float | None):
        samples = CrackAutoDetector._sample_width_profile_from_contrast(contrast, crack.points, meter_per_pixel)
        crack.width_samples = CrackAutoDetector._pick_min_mid_max(samples)

    @staticmethod
    def _sample_width_profile_from_contrast(contrast: np.ndarray, points: list[Point], meter_per_pixel: float | None) -> list[WidthSample]:
        if len(points) < 2:
            return []
        local_thr = max(10, int(np.percentile(contrast, 91)))
        samples: list[WidthSample] = []

        for idx in range(len(points) - 1):
            p1 = np.array(points[idx], dtype=float)
            p2 = np.array(points[idx + 1], dtype=float)
            v = p2 - p1
            n = np.linalg.norm(v)
            if n < 1e-6:
                continue
            dirv = v / n
            normal = np.array([-dirv[1], dirv[0]])
            center = (p1 + p2) / 2
            left = CrackAutoDetector._trace_edge(contrast, center, -normal, local_thr)
            right = CrackAutoDetector._trace_edge(contrast, center, normal, local_thr)
            if left is None or right is None:
                continue
            a = tuple(left.tolist())
            b = tuple(right.tolist())
            width_px = distance(a, b)
            if width_px < 1.2 or width_px > 55:
                continue
            width_mm = width_px * meter_per_pixel * 1000 if meter_per_pixel else width_px
            samples.append(WidthSample(p1=a, p2=b, width_mm=width_mm))
        return samples

    @staticmethod
    def _pick_min_mid_max(samples: list[WidthSample]) -> list[WidthSample]:
        if not samples:
            return []
        min_s = min(samples, key=lambda s: s.width_mm)
        mid_s = samples[len(samples) // 2]
        max_s = max(samples, key=lambda s: s.width_mm)
        return [min_s, mid_s, max_s]

    @staticmethod
    def _trace_edge(contrast: np.ndarray, center: np.ndarray, direction: np.ndarray, thr: float):
        h, w = contrast.shape
        last_line = None
        for step in range(1, 30):
            p = center + direction * step
            x, y = int(round(p[0])), int(round(p[1]))
            if x < 0 or y < 0 or x >= w or y >= h:
                break
            val = contrast[y, x]
            if val >= thr:
                last_line = np.array([x, y], dtype=float)
            elif last_line is not None:
                return last_line
        return last_line

    @staticmethod
    def _bbox(points: list[Point]) -> tuple[float, float, float, float]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _overlaps_existing(box, boxes, threshold: float = 0.65) -> bool:
        x1, y1, x2, y2 = box
        area = max(1.0, (x2 - x1) * (y2 - y1))
        for bx1, by1, bx2, by2 in boxes:
            ix1, iy1 = max(x1, bx1), max(y1, by1)
            ix2, iy2 = min(x2, bx2), min(y2, by2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            inter = (ix2 - ix1) * (iy2 - iy1)
            if inter / area > threshold:
                return True
        return False
