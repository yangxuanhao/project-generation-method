import csv
import shutil
from pathlib import Path
from PIL import Image
from app.core.database import execute, log_action
from app.core.config import IMPORT_DIR
from app.algorithms.image_hash import md5_file, average_hash, hamming_hex
from app.algorithms.text_quality import normalize_text


def inspect_image_folder(folder: str) -> list[dict]:
    path = Path(folder)
    result = []
    hashes = {}
    for p in sorted(path.glob('*')):
        if p.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
            continue
        row = {'filename': p.name, 'path': str(p), 'status': '正常', 'issues': []}
        try:
            img = Image.open(p)
            row['width'], row['height'] = img.size
            row['md5'] = md5_file(p)
            ah = average_hash(p)
            row['ahash'] = ah
            if min(img.size) < 128:
                row['issues'].append('图片尺寸过小')
            if row['md5'] in hashes:
                row['issues'].append(f"完全重复：{hashes[row['md5']]}")
            else:
                for old_hash, old_name in hashes.items():
                    pass
            for other in result:
                if other.get('ahash') and hamming_hex(ah, other['ahash']) <= 6:
                    row['issues'].append(f"近似重复：{other['filename']}")
                    break
            hashes[row['md5']] = p.name
        except Exception as exc:
            row['status'] = '异常'
            row['issues'].append(f'无法读取：{exc}')
            row['width'], row['height'] = 0, 0
        if row['issues']:
            row['status'] = '需人工确认'
        result.append(row)
    return result


def import_images(project_id: int, folder: str, username: str) -> list[dict]:
    records = inspect_image_folder(folder)
    target_dir = IMPORT_DIR / f"project_{project_id}_images"
    target_dir.mkdir(parents=True, exist_ok=True)
    for idx, row in enumerate(records, start=1):
        source = Path(row['path'])
        target = target_dir / source.name
        if source.exists() and source.resolve() != target.resolve():
            shutil.copy2(source, target)
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,width,height,status,risk_tags,is_duplicate,is_low_confidence,assigned_to,qc_status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (project_id, f"IMP-IMG-{idx:04d}", 'image', source.name, str(target), row.get('width',0), row.get('height',0), '未开始', ';'.join(row['issues']), 1 if any('重复' in i for i in row['issues']) else 0, 1 if row['status'] != '正常' else 0, 'labeler', '未质检'))
        row['sample_id'] = sid
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (project_id, project_id))
    log_action(username, '导入图片样本', f"项目{project_id} 导入 {len(records)} 张图片")
    return records


def inspect_text_csv(csv_path: str) -> list[dict]:
    p = Path(csv_path)
    rows = []
    seen = {}
    with p.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for i, item in enumerate(reader, start=1):
            text = item.get('text') or item.get('content') or ''
            label = item.get('label') or ''
            issues = []
            n = normalize_text(text)
            if not text.strip(): issues.append('文本为空')
            if 0 < len(text.strip()) < 8: issues.append('文本过短')
            if not label.strip(): issues.append('标签缺失')
            if n in seen: issues.append(f"重复文本：第{seen[n]}行")
            seen[n] = i
            rows.append({'line': i, 'text': text, 'label': label, 'issues': issues, 'status': '需人工确认' if issues else '正常'})
    return rows


def import_text_csv(project_id: int, csv_path: str, username: str) -> list[dict]:
    records = inspect_text_csv(csv_path)
    for row in records:
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,text_content,status,risk_tags,is_duplicate,is_low_confidence,assigned_to,qc_status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (project_id, f"IMP-TXT-{row['line']:04d}", 'text', Path(csv_path).name, csv_path, row['text'], '未开始', ';'.join(row['issues']), 1 if any('重复' in i for i in row['issues']) else 0, 1 if row['issues'] else 0, 'labeler', '未质检'))
        if row['label']:
            execute("INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment) VALUES(?,?,?,?,?,?,?,?)", (sid, row['label'], 'text_class', 0.8, '导入', '待确认', username, 'CSV导入标签'))
        row['sample_id'] = sid
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (project_id, project_id))
    log_action(username, '导入文本样本', f"项目{project_id} 导入 {len(records)} 条文本")
    return records
