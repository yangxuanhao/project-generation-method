from app.algorithms.iou import bbox_iou


def check_bbox(annotation: dict, image_w: int, image_h: int) -> list[dict]:
    issues = []
    x, y, w, h = float(annotation['x']), float(annotation['y']), float(annotation['w']), float(annotation['h'])
    area = w * h
    image_area = max(1, image_w * image_h)
    if x < 0 or y < 0 or x + w > image_w or y + h > image_h:
        issues.append({"type": "标注框越界", "severity": "高", "rule": "BBoxBoundary", "position": f"x={x:.0f},y={y:.0f},w={w:.0f},h={h:.0f}", "suggestion": "将框调整到图片有效区域内。"})
    if area < image_area * 0.002:
        issues.append({"type": "标注框过小", "severity": "中", "rule": "MinBoxArea", "position": f"面积={area:.0f}", "suggestion": "确认是否小目标，若不是请删除或放大到目标真实边界。"})
    if area > image_area * 0.65:
        issues.append({"type": "标注框过大", "severity": "中", "rule": "MaxBoxArea", "position": f"面积占比={area/image_area:.1%}", "suggestion": "检查是否误框到背景或整图。"})
    if min(abs(x), abs(y), abs(image_w - (x + w)), abs(image_h - (y + h))) <= 2:
        issues.append({"type": "异常贴边框", "severity": "低", "rule": "EdgeTouch", "position": "贴近图片边缘", "suggestion": "贴边目标允许保留，但需确认边界贴合目标。"})
    if w <= 0 or h <= 0:
        issues.append({"type": "无效标注框", "severity": "高", "rule": "NonPositiveBox", "position": "宽高为0", "suggestion": "重新绘制标注框。"})
    ratio = max(w / max(h, 1), h / max(w, 1))
    if ratio > 8:
        issues.append({"type": "长宽比异常", "severity": "低", "rule": "AspectRatio", "position": f"比例={ratio:.1f}", "suggestion": "检查是否把线状背景误标为目标。"})
    return issues


def check_duplicate_boxes(annotations: list[dict]) -> list[dict]:
    issues = []
    for i, a in enumerate(annotations):
        for b in annotations[i + 1:]:
            score = bbox_iou(a, b)
            if score > 0.82 and a.get('label') == b.get('label'):
                issues.append({"type": "同目标重复框", "severity": "高", "rule": "DuplicateIoU", "position": f"对象{a['id']} 与 对象{b['id']} IoU={score:.2f}", "suggestion": "合并或删除重复目标框。", "annotation_id": a.get('id')})
            elif score > 0.65:
                issues.append({"type": "高度重叠框", "severity": "中", "rule": "OverlapIoU", "position": f"对象{a['id']} 与 对象{b['id']} IoU={score:.2f}", "suggestion": "确认是否两个真实相邻目标，若为同一目标请保留一个框。", "annotation_id": a.get('id')})
    return issues
