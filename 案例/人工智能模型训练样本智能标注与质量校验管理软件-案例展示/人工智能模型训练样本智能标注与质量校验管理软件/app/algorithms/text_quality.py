import re
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def check_text_sample(text: str, labels: list[str] | None = None, reason: str = "") -> list[dict]:
    issues = []
    raw = text or ""
    if not raw.strip():
        issues.append({"type": "文本为空", "severity": "高", "rule": "EmptyText", "position": "全文", "suggestion": "剔除空文本或补充原始内容。"})
    if 0 < len(raw.strip()) < 8:
        issues.append({"type": "文本过短", "severity": "中", "rule": "ShortText", "position": f"长度={len(raw.strip())}", "suggestion": "检查是否缺失上下文。"})
    if labels is not None and not labels:
        issues.append({"type": "标签为空", "severity": "高", "rule": "EmptyLabel", "position": "标签字段", "suggestion": "至少选择一个有效标签。"})
    if labels and "退款" in labels and "物流" in labels:
        issues.append({"type": "标签冲突", "severity": "中", "rule": "ExclusiveIntent", "position": "退款/物流", "suggestion": "主诉求只能保留一个，另一个可放入备注。"})
    if reason is not None and len(reason.strip()) < 10:
        issues.append({"type": "评价理由过短", "severity": "低", "rule": "ReasonLength", "position": "评价理由", "suggestion": "补充具体判断依据，至少10字。"})
    return issues
