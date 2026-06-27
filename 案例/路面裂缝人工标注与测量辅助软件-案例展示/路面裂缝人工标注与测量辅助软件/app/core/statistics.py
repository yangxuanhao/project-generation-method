from __future__ import annotations

from collections import Counter
from .geometry import polyline_length_real


class RoadSectionStatistics:
    """路段级统计：把多张影像中的裂缝汇总为路段调查指标。"""

    @staticmethod
    def summarize_tasks(tasks):
        total_cracks = 0
        total_regions = 0
        total_length_m = 0.0
        total_area_m2 = 0.0
        severe_count = 0
        type_counter = Counter()
        level_counter = Counter()
        width_values = []
        for task in tasks:
            mpp = task.meter_per_pixel
            for crack in task.cracks:
                total_cracks += 1
                length = polyline_length_real(crack.points, mpp)
                if not mpp:
                    length = length / 180
                total_length_m += length
                type_counter[crack.crack_type] += 1
                level_counter[crack.severity] += 1
                if crack.severity in ["严重", "较重"]:
                    severe_count += 1
                if crack.avg_width_mm:
                    width_values.append(crack.avg_width_mm)
            for region in task.regions:
                total_regions += 1
                total_area_m2 += region.area_m2
                level_counter[region.severity] += 1
                if region.severity in ["严重", "较重"]:
                    severe_count += 1
        avg_width = sum(width_values) / len(width_values) if width_values else 0.0
        risk_index = min(100, int(total_length_m * 3 + total_area_m2 * 2 + severe_count * 8 + total_cracks * 1.5))
        return {
            "裂缝总数": total_cracks,
            "网裂区域数": total_regions,
            "裂缝总长度": total_length_m,
            "网裂总面积": total_area_m2,
            "平均宽度": avg_width,
            "较重及严重数量": severe_count,
            "病害指数": risk_index,
            "类型分布": dict(type_counter),
            "等级分布": dict(level_counter),
        }
