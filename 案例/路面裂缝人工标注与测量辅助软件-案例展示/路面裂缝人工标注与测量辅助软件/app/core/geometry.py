from __future__ import annotations

import math
from typing import List, Tuple

Point = Tuple[float, float]


def distance(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def polyline_length(points: List[Point]) -> float:
    return sum(distance(points[i - 1], points[i]) for i in range(1, len(points)))


def polyline_length_real(points: List[Point], meter_per_pixel: float | None) -> float:
    if not meter_per_pixel:
        return polyline_length(points)
    return polyline_length(points) * meter_per_pixel


def polygon_area_pixels(points: List[Point]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_area_real(points: List[Point], meter_per_pixel: float | None) -> float:
    area_px = polygon_area_pixels(points)
    if not meter_per_pixel:
        return area_px
    return area_px * (meter_per_pixel ** 2)


def smooth_polyline(points: List[Point], strength: float = 0.55, rounds: int = 2) -> List[Point]:
    if len(points) <= 2:
        return list(points)
    result = list(points)
    for _ in range(rounds):
        new_points = [result[0]]
        for i in range(1, len(result) - 1):
            px, py = result[i - 1]
            x, y = result[i]
            nx, ny = result[i + 1]
            sx = x * (1 - strength) + (px + nx) / 2 * strength
            sy = y * (1 - strength) + (py + ny) / 2 * strength
            new_points.append((sx, sy))
        new_points.append(result[-1])
        result = new_points
    return result


def bounding_box(points: List[Point]) -> tuple[float, float, float, float]:
    if not points:
        return 0, 0, 0, 0
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def nearest_point_index(points: List[Point], p: Point, radius: float = 12) -> int:
    best = -1
    best_d = radius
    for i, q in enumerate(points):
        d = distance(p, q)
        if d < best_d:
            best_d = d
            best = i
    return best
