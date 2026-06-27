from __future__ import annotations


class RepairMaterialEstimator:
    """修复材料估算：把裂缝量测结果转换为养护材料建议。"""

    METHODS = ["灌缝胶修补", "开槽灌缝", "沥青冷补料", "局部铣刨重铺", "裂缝封层", "网裂区域罩面"]

    @staticmethod
    def estimate_sealant(length_m: float, avg_width_mm: float, depth_mm: float = 20, loss_rate: float = 0.08) -> float:
        width_m = max(avg_width_mm, 1.2) / 1000
        depth_m = depth_mm / 1000
        volume_m3 = length_m * width_m * depth_m
        return volume_m3 * 1000 * (1 + loss_rate)

    @staticmethod
    def estimate_patch_material(area_m2: float, thickness_cm: float = 4, density_ton_m3: float = 2.3, loss_rate: float = 0.1) -> float:
        volume_m3 = area_m2 * (thickness_cm / 100)
        return volume_m3 * density_ton_m3 * (1 + loss_rate)

    @staticmethod
    def recommend(severity: str, crack_type: str) -> str:
        if crack_type in ["网状裂缝", "龟裂", "块状裂缝"]:
            return "网裂区域罩面" if severity in ["较重", "严重"] else "裂缝封层"
        if severity in ["轻微", "一般"]:
            return "灌缝胶修补"
        if severity == "较重":
            return "开槽灌缝"
        return "局部铣刨重铺"

    @staticmethod
    def estimate_for_crack(length_m: float, avg_width_mm: float, severity: str, crack_type: str, method: str | None = None):
        chosen = method or RepairMaterialEstimator.recommend(severity, crack_type)
        if chosen == "灌缝胶修补":
            return chosen, RepairMaterialEstimator.estimate_sealant(length_m, avg_width_mm, 18, 0.08), "升"
        if chosen == "开槽灌缝":
            return chosen, RepairMaterialEstimator.estimate_sealant(length_m, max(avg_width_mm, 8), 35, 0.12), "升"
        if chosen == "裂缝封层":
            return chosen, max(length_m * 0.25, 0.5), "平方米"
        if chosen == "局部铣刨重铺":
            return chosen, max(length_m * 0.8, 1.0) * 0.04 * 2.3 * 1.12, "吨"
        if chosen == "沥青冷补料":
            return chosen, max(length_m * 0.15, 0.2), "吨"
        return chosen, max(length_m * 0.6, 0.8), "平方米"
