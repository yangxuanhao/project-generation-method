from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime
from .geometry import polyline_length_real
from .statistics import RoadSectionStatistics
from .quality import AnnotationQualityChecker


class CrackReportGenerator:
    """成果导出：JSON、CSV、TXT报告。"""

    def __init__(self, export_dir: Path):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, tasks):
        path = self.export_dir / f"crack_annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data = [task.to_dict() for task in tasks]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def export_csv(self, tasks):
        path = self.export_dir / f"crack_measurements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["任务编号", "道路名称", "位置说明", "经度", "纬度", "方向", "道路等级", "影像来源", "裂缝编号", "类型", "严重等级", "长度米", "平均宽度毫米", "最大宽度毫米", "复核状态", "修复方式", "材料量", "单位"])
            for task in tasks:
                for crack in task.cracks:
                    length = polyline_length_real(crack.points, task.meter_per_pixel)
                    if not task.meter_per_pixel:
                        length = length / 180
                    writer.writerow([task.task_id, task.road_name, task.location_name, task.longitude, task.latitude, task.direction, task.road_level, task.source_type, crack.crack_id, crack.crack_type, crack.severity, f"{length:.3f}", f"{crack.avg_width_mm:.2f}", f"{crack.max_width_mm:.2f}", crack.review_status, crack.repair_method, f"{crack.material_amount:.2f}", crack.material_unit])
        return path

    def export_txt_report(self, tasks):
        path = self.export_dir / f"road_crack_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        stat = RoadSectionStatistics.summarize_tasks(tasks)
        lines = []
        lines.append("路面裂缝人工标注与测量分析报告")
        lines.append("=" * 36)
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"任务数量：{len(tasks)}")
        lines.append("")
        lines.append("一、路段病害汇总")
        lines.append(f"裂缝总数：{stat['裂缝总数']} 条")
        lines.append(f"网裂区域数：{stat['网裂区域数']} 个")
        lines.append(f"裂缝总长度：{stat['裂缝总长度']:.2f} 米")
        lines.append(f"网裂总面积：{stat['网裂总面积']:.2f} 平方米")
        lines.append(f"平均宽度：{stat['平均宽度']:.2f} 毫米")
        lines.append(f"较重及严重数量：{stat['较重及严重数量']} 个")
        lines.append(f"病害指数：{stat['病害指数']} / 100")
        lines.append("")
        lines.append("二、类型分布")
        for k, v in stat["类型分布"].items():
            lines.append(f"{k}：{v}")
        lines.append("")
        lines.append("三、严重等级分布")
        for k, v in stat["等级分布"].items():
            lines.append(f"{k}：{v}")
        lines.append("")
        lines.append("四、任务明细与质量检查")
        for task in tasks:
            score, details = AnnotationQualityChecker.score(task)
            lines.append(f"任务：{task.road_name} / {task.task_id} / 质量分：{score}")
            lines.append(f"影像：{task.image_path}")
            lines.append(f"位置说明：{task.location_name}")
            lines.append(f"坐标：{task.latitude}, {task.longitude}")
            lines.append(f"方向/等级：{task.direction} / {task.road_level}")
            lines.append(f"影像来源：{task.source_type}")
            lines.append(f"路段备注：{task.section_note}")
            lines.append(f"比例尺：{task.meter_per_pixel if task.meter_per_pixel else '未标定'}")
            for d in details[:8]:
                lines.append(f"- {d}")
            lines.append("")
        lines.append("五、养护建议")
        if stat["病害指数"] >= 70:
            lines.append("该路段病害指数较高，建议优先安排现场复核，并对严重裂缝实施开槽灌缝或局部铣刨重铺。")
        elif stat["病害指数"] >= 40:
            lines.append("该路段存在较明显裂缝病害，建议近期进行灌缝、封层和复核性检测。")
        else:
            lines.append("该路段当前病害指数较低，可纳入日常巡查和预防性养护计划。")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
