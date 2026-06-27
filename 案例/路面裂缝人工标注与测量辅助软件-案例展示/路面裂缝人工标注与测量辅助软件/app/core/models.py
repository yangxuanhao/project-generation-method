from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import uuid

Point = Tuple[float, float]


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass
class User:
    username: str
    password_hash: str
    role: str = "标注员"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "User":
        return User(
            username=data.get("username", ""),
            password_hash=data.get("password_hash", ""),
            role=data.get("role", "标注员"),
            created_at=data.get("created_at", "") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


@dataclass
class WidthSample:
    p1: Point
    p2: Point
    width_mm: float
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {"p1": list(self.p1), "p2": list(self.p2), "width_mm": self.width_mm, "created_at": self.created_at}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WidthSample":
        return WidthSample(tuple(data.get("p1", (0, 0))), tuple(data.get("p2", (0, 0))), float(data.get("width_mm", 0)), data.get("created_at", ""))


@dataclass
class ReviewLog:
    crack_id: str
    reviewer: str
    result: str
    comment: str
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ReviewLog":
        return ReviewLog(
            crack_id=data.get("crack_id", ""),
            reviewer=data.get("reviewer", ""),
            result=data.get("result", ""),
            comment=data.get("comment", ""),
            created_at=data.get("created_at", ""),
        )


@dataclass
class CrackObject:
    crack_id: str = field(default_factory=lambda: new_id("裂缝"))
    points: List[Point] = field(default_factory=list)
    crack_type: str = "待判定"
    suggestion_type: str = "待判定"
    severity: str = "未评估"
    review_status: str = "待复核"
    review_comment: str = ""
    locked: bool = False
    ignored: bool = False
    source: str = "人工描绘"
    width_samples: List[WidthSample] = field(default_factory=list)
    repair_method: str = "灌缝胶修补"
    material_amount: float = 0.0
    material_unit: str = "升"
    station: str = "未绑定"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def avg_width_mm(self) -> float:
        if not self.width_samples:
            return 0.0
        return sum(s.width_mm for s in self.width_samples) / len(self.width_samples)

    @property
    def max_width_mm(self) -> float:
        if not self.width_samples:
            return 0.0
        return max(s.width_mm for s in self.width_samples)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["points"] = [list(p) for p in self.points]
        data["width_samples"] = [s.to_dict() for s in self.width_samples]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CrackObject":
        crack = CrackObject(
            crack_id=data.get("crack_id") or new_id("裂缝"),
            points=[tuple(p) for p in data.get("points", [])],
            crack_type=data.get("crack_type", "待判定"),
            suggestion_type=data.get("suggestion_type", "待判定"),
            severity=data.get("severity", "未评估"),
            review_status=data.get("review_status", "待复核"),
            review_comment=data.get("review_comment", ""),
            locked=bool(data.get("locked", False)),
            ignored=bool(data.get("ignored", False)),
            source=data.get("source", "人工描绘"),
            repair_method=data.get("repair_method", "灌缝胶修补"),
            material_amount=float(data.get("material_amount", 0)),
            material_unit=data.get("material_unit", "升"),
            station=data.get("station", "未绑定"),
            created_at=data.get("created_at", ""),
        )
        crack.width_samples = [WidthSample.from_dict(x) for x in data.get("width_samples", [])]
        return crack


@dataclass
class CrackRegion:
    region_id: str = field(default_factory=lambda: new_id("网裂区"))
    polygon_points: List[Point] = field(default_factory=list)
    area_m2: float = 0.0
    density: float = 0.0
    severity: str = "未评估"
    review_status: str = "待复核"
    comment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["polygon_points"] = [list(p) for p in self.polygon_points]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CrackRegion":
        return CrackRegion(
            region_id=data.get("region_id") or new_id("网裂区"),
            polygon_points=[tuple(p) for p in data.get("polygon_points", [])],
            area_m2=float(data.get("area_m2", 0)),
            density=float(data.get("density", 0)),
            severity=data.get("severity", "未评估"),
            review_status=data.get("review_status", "待复核"),
            comment=data.get("comment", ""),
        )


@dataclass
class CandidateCrack:
    candidate_id: str = field(default_factory=lambda: new_id("疑似"))
    points: List[Point] = field(default_factory=list)
    score: float = 0.0
    status: str = "待确认"
    note: str = "暗线增强候选"

    def to_dict(self) -> Dict[str, Any]:
        return {"candidate_id": self.candidate_id, "points": [list(p) for p in self.points], "score": self.score, "status": self.status, "note": self.note}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CandidateCrack":
        return CandidateCrack(data.get("candidate_id") or new_id("疑似"), [tuple(p) for p in data.get("points", [])], float(data.get("score", 0)), data.get("status", "待确认"), data.get("note", "暗线增强候选"))


@dataclass
class AnnotationTask:
    task_id: str = field(default_factory=lambda: new_id("任务"))
    road_name: str = "未命名道路"
    image_path: str = ""
    pavement_type: str = "沥青路面"
    station_start: str = "K0+000"
    station_end: str = "K0+100"
    lane: str = "上行一车道"
    location_name: str = "未注明位置"
    longitude: str = ""
    latitude: str = ""
    road_level: str = "一般公路"
    direction: str = "上行"
    section_note: str = ""
    source_type: str = "普通路面影像"
    collector: str = "演示采集员"
    annotator: str = ""
    status: str = "待标注"
    meter_per_pixel: Optional[float] = None
    cracks: List[CrackObject] = field(default_factory=list)
    regions: List[CrackRegion] = field(default_factory=list)
    candidates: List[CandidateCrack] = field(default_factory=list)
    review_logs: List[ReviewLog] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def touch(self):
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["cracks"] = [c.to_dict() for c in self.cracks]
        data["regions"] = [r.to_dict() for r in self.regions]
        data["candidates"] = [c.to_dict() for c in self.candidates]
        data["review_logs"] = [r.to_dict() for r in self.review_logs]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AnnotationTask":
        task = AnnotationTask(
            task_id=data.get("task_id") or new_id("任务"),
            road_name=data.get("road_name", "未命名道路"),
            image_path=data.get("image_path", ""),
            pavement_type=data.get("pavement_type", "沥青路面"),
            station_start=data.get("station_start", "K0+000"),
            station_end=data.get("station_end", "K0+100"),
            lane=data.get("lane", "上行一车道"),
            location_name=data.get("location_name", "未注明位置"),
            longitude=data.get("longitude", ""),
            latitude=data.get("latitude", ""),
            road_level=data.get("road_level", "一般公路"),
            direction=data.get("direction", "上行"),
            section_note=data.get("section_note", ""),
            source_type=data.get("source_type", "普通路面影像"),
            collector=data.get("collector", "演示采集员"),
            annotator=data.get("annotator", ""),
            status=data.get("status", "待标注"),
            meter_per_pixel=data.get("meter_per_pixel", None),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
        task.cracks = [CrackObject.from_dict(x) for x in data.get("cracks", [])]
        task.regions = [CrackRegion.from_dict(x) for x in data.get("regions", [])]
        task.candidates = [CandidateCrack.from_dict(x) for x in data.get("candidates", [])]
        task.review_logs = [ReviewLog.from_dict(x) for x in data.get("review_logs", [])]
        return task
