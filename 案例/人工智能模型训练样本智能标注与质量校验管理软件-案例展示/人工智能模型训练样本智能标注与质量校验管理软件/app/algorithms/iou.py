def bbox_iou(a: dict, b: dict) -> float:
    ax1, ay1, ax2, ay2 = float(a['x']), float(a['y']), float(a['x'] + a['w']), float(a['y'] + a['h'])
    bx1, by1, bx2, by2 = float(b['x']), float(b['y']), float(b['x'] + b['w']), float(b['y'] + b['h'])
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union else 0.0
