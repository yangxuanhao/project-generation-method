import json
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from app.core.config import EXPORT_DIR
from app.core.database import fetch_all, execute, log_action
from app.services.dataset_service import get_labels, dashboard_metrics


def delivery_check(project_id: int) -> tuple[bool, list[str]]:
    metrics = dashboard_metrics(project_id)
    problems = []
    if metrics.get('pending_total', 0) > 0: problems.append(f"存在未标注样本 {metrics['pending_total']} 个")
    if metrics.get('qc_pending_total', 0) > 0: problems.append(f"存在待质检样本 {metrics['qc_pending_total']} 个")
    if metrics.get('rework_total', 0) > 0: problems.append(f"存在返工样本 {metrics['rework_total']} 个")
    if metrics.get('health_score', 0) < 80: problems.append(f"健康度 {metrics.get('health_score',0)} 未达到建议交付线 80")
    if metrics.get('balance_score', 0) < 70: problems.append("标签分布不均衡")
    return len(problems) == 0, problems


def _project_dir(project_id: int, fmt: str) -> Path:
    out = EXPORT_DIR / f"project_{project_id}_{fmt}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def export_yolo(project_id: int, username: str) -> Path:
    out = _project_dir(project_id, 'yolo')
    labels = [x['name'] for x in get_labels(project_id)]
    (out / 'classes.txt').write_text('\n'.join(labels), encoding='utf-8')
    samples = fetch_all("SELECT * FROM samples WHERE project_id=? AND sample_type='image'", (project_id,))
    for s in samples:
        anns = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND annotation_type='bbox' AND status!='已删除'", (s['id'],))
        rows = []
        for a in anns:
            cls = labels.index(a['label']) if a['label'] in labels else 0
            xc = (a['x'] + a['w'] / 2) / max(1, s['width'])
            yc = (a['y'] + a['h'] / 2) / max(1, s['height'])
            rows.append(f"{cls} {xc:.6f} {yc:.6f} {a['w']/max(1,s['width']):.6f} {a['h']/max(1,s['height']):.6f}")
        (out / f"{Path(s['filename']).stem}.txt").write_text('\n'.join(rows), encoding='utf-8')
    zip_path = EXPORT_DIR / f"project_{project_id}_YOLO.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in out.glob('*'):
            z.write(p, p.name)
    ok, problems = delivery_check(project_id)
    execute("INSERT INTO export_records(project_id,format,output_path,check_result,created_by) VALUES(?,?,?,?,?)", (project_id, 'YOLO', str(zip_path), '通过' if ok else ';'.join(problems), username))
    log_action(username, '导出YOLO', str(zip_path))
    return zip_path


def export_coco(project_id: int, username: str) -> Path:
    out = _project_dir(project_id, 'coco')
    labels = get_labels(project_id)
    cats = [{'id': i+1, 'name': l['name']} for i, l in enumerate(labels)]
    label_map = {c['name']: c['id'] for c in cats}
    images = []
    annotations = []
    aid = 1
    samples = fetch_all("SELECT * FROM samples WHERE project_id=? AND sample_type='image'", (project_id,))
    for s in samples:
        images.append({'id': s['id'], 'file_name': s['filename'], 'width': s['width'], 'height': s['height']})
        anns = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND annotation_type='bbox' AND status!='已删除'", (s['id'],))
        for a in anns:
            annotations.append({'id': aid, 'image_id': s['id'], 'category_id': label_map.get(a['label'], 1), 'bbox': [a['x'], a['y'], a['w'], a['h']], 'area': a['w']*a['h'], 'iscrowd': 0})
            aid += 1
    path = out / 'annotations_coco.json'
    path.write_text(json.dumps({'images': images, 'annotations': annotations, 'categories': cats}, ensure_ascii=False, indent=2), encoding='utf-8')
    execute("INSERT INTO export_records(project_id,format,output_path,check_result,created_by) VALUES(?,?,?,?,?)", (project_id, 'COCO JSON', str(path), '已生成COCO结构文件', username))
    log_action(username, '导出COCO', str(path))
    return path


def export_pascal_voc(project_id: int, username: str) -> Path:
    out = _project_dir(project_id, 'voc')
    samples = fetch_all("SELECT * FROM samples WHERE project_id=? AND sample_type='image'", (project_id,))
    for s in samples:
        root = Element('annotation')
        SubElement(root, 'filename').text = s['filename']
        size = SubElement(root, 'size')
        SubElement(size, 'width').text = str(s['width']); SubElement(size, 'height').text = str(s['height']); SubElement(size, 'depth').text = '3'
        for a in fetch_all("SELECT * FROM annotations WHERE sample_id=? AND annotation_type='bbox' AND status!='已删除'", (s['id'],)):
            obj = SubElement(root, 'object'); SubElement(obj, 'name').text = a['label']
            bnd = SubElement(obj, 'bndbox')
            SubElement(bnd, 'xmin').text = str(int(a['x'])); SubElement(bnd, 'ymin').text = str(int(a['y']))
            SubElement(bnd, 'xmax').text = str(int(a['x']+a['w'])); SubElement(bnd, 'ymax').text = str(int(a['y']+a['h']))
        xml = minidom.parseString(tostring(root)).toprettyxml(indent='  ')
        (out / f"{Path(s['filename']).stem}.xml").write_text(xml, encoding='utf-8')
    execute("INSERT INTO export_records(project_id,format,output_path,check_result,created_by) VALUES(?,?,?,?,?)", (project_id, 'Pascal VOC XML', str(out), '已生成VOC XML目录', username))
    log_action(username, '导出VOC', str(out))
    return out


def export_text_jsonl(project_id: int, username: str) -> Path:
    out = _project_dir(project_id, 'jsonl')
    path = out / 'text_training_samples.jsonl'
    rows = []
    samples = fetch_all("SELECT * FROM samples WHERE project_id=? AND sample_type='text'", (project_id,))
    for s in samples:
        anns = fetch_all("SELECT * FROM annotations WHERE sample_id=? AND status!='已删除'", (s['id'],))
        labels = [a['label'] for a in anns]
        rows.append(json.dumps({'id': s['sample_code'], 'text': s['text_content'], 'labels': labels, 'split': 'train'}, ensure_ascii=False))
    path.write_text('\n'.join(rows), encoding='utf-8')
    execute("INSERT INTO export_records(project_id,format,output_path,check_result,created_by) VALUES(?,?,?,?,?)", (project_id, 'JSONL', str(path), '已生成文本训练JSONL', username))
    log_action(username, '导出文本JSONL', str(path))
    return path
