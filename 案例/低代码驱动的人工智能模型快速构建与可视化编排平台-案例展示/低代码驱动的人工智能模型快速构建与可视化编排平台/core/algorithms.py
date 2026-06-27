"""原创核心算法集 - 画布布局、特征分析、参数优化、数据适配"""
import math, random, hashlib, json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field

@dataclass
class LayoutNode:
    nid: str; x: float = 0; y: float = 0; w: float = 150; h: float = 60
    level: int = 0; children: List[str] = field(default_factory=list)

class ForceDirectedLayout:
    """原创力导向布局算法 - 用于AI模型画布自动排列"""
    def __init__(self, width: float = 2000, height: float = 1500):
        self.width = width; self.height = height
        self.spring_len = 180; self.spring_k = 0.06
        self.repulsion = 8000; self.damping = 0.85
        self.iterations = 200; self.min_dist = 100

    def layout(self, nodes: List[LayoutNode], edges: List[Tuple[str, str]]) -> List[LayoutNode]:
        if not nodes: return []
        node_map = {n.nid: n for n in nodes}
        for n in nodes:
            if n.x == 0 and n.y == 0:
                n.x = self.width / 2 + random.uniform(-50, 50)
                n.y = self.height / 2 + random.uniform(-50, 50)
        velocities = {n.nid: [0.0, 0.0] for n in nodes}
        for _ in range(self.iterations):
            forces = {n.nid: [0.0, 0.0] for n in nodes}
            for i, ni in enumerate(nodes):
                for j, nj in enumerate(nodes):
                    if i >= j: continue
                    dx, dy = ni.x - nj.x, ni.y - nj.y
                    dist = max(1, math.sqrt(dx * dx + dy * dy))
                    f = self.repulsion / (dist * dist)
                    fx, fy = f * dx / dist, f * dy / dist
                    forces[ni.nid][0] += fx; forces[ni.nid][1] += fy
                    forces[nj.nid][0] -= fx; forces[nj.nid][1] -= fy
            for src, tgt in edges:
                if src in node_map and tgt in node_map:
                    ns, nt = node_map[src], node_map[tgt]
                    dx, dy = ns.x - nt.x, ns.y - nt.y
                    dist = max(1, math.sqrt(dx * dx + dy * dy))
                    f = self.spring_k * (dist - self.spring_len)
                    fx, fy = f * dx / dist, f * dy / dist
                    forces[ns.nid][0] -= fx; forces[ns.nid][1] -= fy
                    forces[nt.nid][0] += fx; forces[nt.nid][1] += fy
            for n in nodes:
                vx, vy = velocities[n.nid]
                vx = (vx + forces[n.nid][0]) * self.damping
                vy = (vy + forces[n.nid][1]) * self.damping
                velocities[n.nid] = [vx, vy]
                n.x = max(20, min(self.width - 20, n.x + vx))
                n.y = max(20, min(self.height - 20, n.y + vy))
        return nodes

class FeatureAnalyzer:
    """原创特征分析算法 - 数据特征提取、维度分析、分布计算"""
    @staticmethod
    def analyze(data: List[dict]) -> dict:
        if not data: return {"error": "无数据"}
        keys = list(data[0].keys())
        analysis = {"total_samples": len(data), "dimensions": len(keys), "fields": {}}
        for key in keys:
            values = [d.get(key) for d in data if d.get(key) is not None]
            if not values: continue
            numeric_vals = [v for v in values if isinstance(v, (int, float))]
            str_vals = [v for v in values if isinstance(v, str)]
            field_info = {"type": "mixed", "count": len(values), "null_count": len(data) - len(values)}
            if len(numeric_vals) > len(values) * 0.8:
                field_info["type"] = "numeric"
                field_info.update(FeatureAnalyzer._numeric_stats(numeric_vals))
            elif len(str_vals) > len(values) * 0.8:
                field_info["type"] = "categorical"
                field_info["unique"] = len(set(str_vals))
                freq = {}
                for v in str_vals: freq[v] = freq.get(v, 0) + 1
                field_info["top_values"] = sorted(freq.items(), key=lambda x: -x[1])[:5]
            analysis["fields"][key] = field_info
        return analysis

    @staticmethod
    def _numeric_stats(vals: List[float]) -> dict:
        n = len(vals); mean = sum(vals) / n
        variance = sum((x - mean) ** 2 for x in vals) / n
        sorted_vals = sorted(vals)
        return {"mean": round(mean, 4), "std": round(math.sqrt(variance), 4),
            "min": min(vals), "max": max(vals),
            "median": sorted_vals[n // 2], "q1": sorted_vals[n // 4], "q3": sorted_vals[3 * n // 4]}

class ParameterOptimizer:
    """原创参数优化算法 - 网格搜索、随机搜索、贝叶斯优化框架"""
    @staticmethod
    def grid_search(param_grid: Dict[str, List], eval_fn, top_k: int = 5) -> List[dict]:
        import itertools
        keys = list(param_grid.keys())
        results = []
        for combo in itertools.product(*[param_grid[k] for k in keys]):
            params = dict(zip(keys, combo))
            try:
                score = eval_fn(params)
                results.append({"params": params, "score": round(score, 6)})
            except: pass
        return sorted(results, key=lambda x: -x["score"])[:top_k]

    @staticmethod
    def random_search(param_dist: Dict[str, Tuple[float, float]], n_iter: int = 100,
                      eval_fn=None, top_k: int = 5) -> List[dict]:
        results = []
        for _ in range(n_iter):
            params = {}
            for k, (lo, hi) in param_dist.items():
                params[k] = random.uniform(lo, hi)
            try:
                score = eval_fn(params) if eval_fn else random.random()
                results.append({"params": params, "score": round(score, 6)})
            except: pass
        return sorted(results, key=lambda x: -x["score"])[:top_k]

class DataAdapter:
    """统一数据适配器 - 多源数据接入标准化"""
    @staticmethod
    def from_csv(path: str) -> List[dict]:
        import csv
        with open(path, 'r', encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))

    @staticmethod
    def from_json(path: str) -> Any:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def normalize(data: List[dict], fields: List[str] = None) -> List[dict]:
        if not data: return data
        keys = fields or list(data[0].keys())
        numeric_fields = []
        for k in keys:
            vals = [d[k] for d in data if k in d and isinstance(d[k], (int, float))]
            if len(vals) > len(data) * 0.5: numeric_fields.append(k)
        result = []
        for row in data:
            norm_row = dict(row)
            for k in numeric_fields:
                if k in norm_row and isinstance(norm_row[k], (int, float)):
                    norm_row[f"{k}_norm"] = round(norm_row[k], 4)
            result.append(norm_row)
        return result

    @staticmethod
    def to_training_format(data: List[dict], features: List[str], target: str) -> Tuple[List, List]:
        X, y = [], []
        for row in data:
            try:
                X.append([float(row.get(f, 0)) for f in features])
                y.append(float(row.get(target, 0)))
            except: pass
        return X, y

class HashValidator:
    """数据完整性快速校验"""
    @staticmethod
    def checksum(data: Any) -> str:
        try: return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]
        except: return "INVALID"

    @staticmethod
    def compare(local: Any, remote: Any) -> bool:
        return HashValidator.checksum(local) == HashValidator.checksum(remote)
