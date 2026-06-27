import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from app.core.config import BASE_DIR, IMAGE_DIR, TEXT_DIR, IMPORT_DIR, EXPORT_DIR, DOCS_DIR
from app.core.database import fetch_one, execute, execute_many


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def _ensure_dirs():
    for p in [IMAGE_DIR, TEXT_DIR, IMPORT_DIR, EXPORT_DIR, DOCS_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def _demo_image(path: Path, idx: int, blur: bool = False) -> tuple[int, int]:
    w, h = 1120, 680
    img = Image.new('RGB', (w, h), (214, 229, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 380], fill=(203, 221, 238))
    d.rectangle([0, 380, w, h], fill=(190, 184, 170))
    for x in range(60, w, 135):
        d.rectangle([x, 80, x + 14, 500], fill=(132, 144, 158))
    for y in range(120, 480, 80):
        d.rectangle([40, y, w - 70, y + 12], fill=(132, 144, 158))
    d.line([720, 60, 1010, 130], fill=(211, 138, 43), width=10)
    for x in range(40, 360, 70):
        d.rectangle([x, 548, x + 48, 584], fill=(241, 176, 33))
        d.line([x, 584, x + 48, 548], fill=(55, 65, 81), width=4)
    rng = random.Random(1000 + idx)
    for i in range(4 + idx % 3):
        x = rng.randint(120, 930)
        y = rng.randint(385, 535)
        scale = rng.uniform(0.85, 1.2)
        body_h = int(85 * scale)
        body_w = int(38 * scale)
        helmet = not (i == 0 and idx % 3 == 0)
        vest = i % 2 == 0
        d.line([x - 12, y + body_h, x - 22, y + body_h + 54], fill=(47, 63, 85), width=8)
        d.line([x + 12, y + body_h, x + 24, y + body_h + 54], fill=(47, 63, 85), width=8)
        d.rectangle([x - body_w // 2, y + 30, x + body_w // 2, y + body_h], fill=(232, 103, 44) if vest else (64, 110, 180))
        d.ellipse([x - 17, y, x + 17, y + 34], fill=(184, 124, 84))
        if helmet:
            d.pieslice([x - 22, y - 7, x + 22, y + 22], 180, 360, fill=(246, 199, 42))
            d.rectangle([x - 22, y + 8, x + 22, y + 15], fill=(232, 180, 24))
    d.rectangle([770, 486, 1035, 580], fill=(92, 111, 128))
    d.rectangle([810, 445, 930, 510], fill=(110, 142, 170))
    d.ellipse([810, 555, 865, 610], fill=(35, 44, 55))
    d.ellipse([965, 555, 1020, 610], fill=(35, 44, 55))
    d.polygon([(530, 460), (585, 558), (475, 558)], fill=(245, 158, 11))
    d.rectangle([525, 515, 536, 546], fill=(31, 41, 55))
    for _ in range(600):
        x = rng.randint(0, w - 1); y = rng.randint(0, h - 1); c = rng.randint(-18, 18)
        r, g, b = img.getpixel((x, y))
        img.putpixel((x, y), (max(0, min(255, r + c)), max(0, min(255, g + c)), max(0, min(255, b + c))))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(2.3))
    img.save(path, quality=92)
    return w, h


def _traffic_image(path: Path, idx: int, rainy: bool = False) -> tuple[int, int]:
    w, h = 1280, 720
    img = Image.new('RGB', (w, h), (202, 216, 226))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 260], fill=(185, 207, 225))
    d.rectangle([0, 260, w, h], fill=(92, 100, 110))
    d.polygon([(450, 260), (830, 260), (1040, 720), (240, 720)], fill=(60, 66, 75))
    for lane in [515, 640, 765]:
        for y in range(300, 700, 90):
            offset = int((y - 260) * 0.18)
            d.rectangle([lane - 5 - offset, y, lane + 5 - offset, y + 45], fill=(238, 238, 210))
    rng = random.Random(3000 + idx)
    for i in range(4 + idx % 4):
        x = rng.randint(180, 940)
        y = rng.randint(330, 610)
        ww = rng.randint(86, 160); hh = rng.randint(42, 74)
        color = [(37, 99, 235), (239, 68, 68), (22, 163, 74), (245, 158, 11)][i % 4]
        d.rounded_rectangle([x, y, x + ww, y + hh], radius=12, fill=color)
        d.rectangle([x + 14, y + 8, x + ww - 18, y + 30], fill=(180, 215, 235))
        d.ellipse([x + 12, y + hh - 14, x + 42, y + hh + 16], fill=(24, 32, 45))
        d.ellipse([x + ww - 42, y + hh - 14, x + ww - 12, y + hh + 16], fill=(24, 32, 45))
    for i in range(3):
        x = 120 + i * 160 + rng.randint(-25, 25); y = 430 + rng.randint(-15, 50)
        d.ellipse([x - 12, y - 28, x + 12, y - 4], fill=(166, 113, 76))
        d.rectangle([x - 14, y, x + 14, y + 56], fill=(31, 94, 141))
        d.line([x - 8, y + 56, x - 18, y + 94], fill=(31, 41, 55), width=6)
        d.line([x + 8, y + 56, x + 20, y + 94], fill=(31, 41, 55), width=6)
    # cyclist
    cx, cy = 910 + rng.randint(-30, 30), 520 + rng.randint(-20, 20)
    d.ellipse([cx - 42, cy + 36, cx + 2, cy + 80], outline=(25, 32, 44), width=5)
    d.ellipse([cx + 46, cy + 36, cx + 90, cy + 80], outline=(25, 32, 44), width=5)
    d.line([cx - 20, cy + 58, cx + 40, cy + 20, cx + 68, cy + 58, cx - 20, cy + 58], fill=(25, 32, 44), width=4)
    d.ellipse([cx + 30, cy - 18, cx + 55, cy + 6], fill=(166, 113, 76))
    d.rectangle([cx + 25, cy + 8, cx + 55, cy + 42], fill=(234, 88, 12))
    # traffic lights / road signs
    d.rectangle([1030, 175, 1050, 455], fill=(55, 65, 81))
    d.rounded_rectangle([1005, 145, 1074, 275], radius=12, fill=(28, 36, 50))
    for k, col in enumerate([(220, 38, 38), (245, 158, 11), (34, 197, 94)]):
        d.ellipse([1025, 160 + k * 36, 1052, 187 + k * 36], fill=col)
    d.polygon([(1115, 330), (1172, 365), (1115, 400), (1058, 365)], fill=(245, 158, 11))
    if rainy:
        for _ in range(220):
            x = rng.randint(0, w); y = rng.randint(0, h)
            d.line([x, y, x + 8, y + 28], fill=(225, 235, 245), width=1)
        img = img.filter(ImageFilter.GaussianBlur(0.8))
    img.save(path, quality=92)
    return w, h


def _defect_image(path: Path, idx: int) -> tuple[int, int]:
    w, h = 1040, 720
    img = Image.new('RGB', (w, h), (236, 240, 244))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 540, w, h], fill=(214, 220, 228))
    rng = random.Random(5000 + idx)
    # workbench table and product tray
    d.rounded_rectangle([95, 105, 945, 590], radius=28, fill=(225, 231, 238), outline=(180, 190, 205), width=3)
    d.rounded_rectangle([150, 160, 890, 530], radius=22, fill=(248, 250, 252), outline=(203, 213, 225), width=2)
    for i in range(3):
        x = 220 + i * 230 + rng.randint(-10, 10)
        y = 260 + rng.randint(-15, 20)
        d.rounded_rectangle([x, y, x + 135, y + 145], radius=18, fill=(218, 230, 244), outline=(128, 143, 163), width=2)
        d.rectangle([x + 26, y + 26, x + 109, y + 115], fill=(191, 219, 254))
    # defects
    if idx % 4 in (0, 1):
        x, y = 250 + rng.randint(0, 420), 220 + rng.randint(0, 210)
        for off in range(0, 50, 9):
            d.line([x + off, y + rng.randint(-4, 4), x + off + 38, y + 8 + rng.randint(-3, 3)], fill=(185, 28, 28), width=3)
    if idx % 3 == 0:
        x, y = 450 + rng.randint(-60, 120), 300 + rng.randint(-40, 70)
        d.ellipse([x, y, x + 70, y + 42], fill=(148, 163, 184), outline=(71, 85, 105), width=2)
    if idx % 5 == 2:
        x, y = 650 + rng.randint(-60, 70), 215 + rng.randint(-10, 90)
        d.ellipse([x, y, x + 95, y + 55], fill=(161, 98, 7))
    if idx in (5, 11):
        img = img.filter(ImageFilter.GaussianBlur(1.6))
    img.save(path, quality=92)
    return w, h


def _real_image_group(folder: str) -> list[tuple[Path, int, int]]:
    """Load packaged realistic demo images by category.

    The project now ships real-world style construction, traffic and industrial
    inspection images instead of synthetic low-fidelity drawings. When the
    database is recreated, samples point to these category folders directly.
    """
    files = sorted((IMAGE_DIR / folder).glob("*.jpg"))
    rows: list[tuple[Path, int, int]] = []
    for path in files:
        with Image.open(path) as img:
            rows.append((path, img.width, img.height))
    return rows


def _write_demo_files():
    _ensure_dirs()
    construction = _real_image_group("construction")
    traffic = _real_image_group("traffic")
    defects = _real_image_group("industrial")

    texts = [
        {"id": "T001", "text": "我申请退款已经三天了，订单还是没有处理，请尽快帮我核实。", "label": "退款", "reason": "用户明确提到退款进度"},
        {"id": "T002", "text": "快递显示签收但我没有收到，能不能帮我查一下物流？", "label": "物流", "reason": "主诉求为物流签收异常"},
        {"id": "T003", "text": "收到的商品破损严重，我要投诉并要求售后处理。", "label": "投诉", "reason": "投诉与售后，但情绪更强烈"},
        {"id": "T004", "text": "这个型号还有黑色库存吗？什么时候可以发货？", "label": "咨询", "reason": "商品咨询"},
        {"id": "T005", "text": "", "label": "其他", "reason": "空文本演示"},
        {"id": "T006", "text": "物流一直不更新，快递停在中转站两天了。", "label": "退款", "reason": "标注存在分歧，实际应为物流"},
        {"id": "T007", "text": "我申请退款已经三天了，订单还是没有处理，请尽快帮我核实。", "label": "售后", "reason": "重复文本且标签不一致"},
        {"id": "T008", "text": "客服答非所问，处理态度非常差。", "label": "投诉", "reason": "差评投诉"},
        {"id": "T009", "text": "可以开发票吗？电子票和纸质票都支持吗？", "label": "咨询", "reason": "票据咨询"},
        {"id": "T010", "text": "退", "label": "退款", "reason": "文本过短"},
        {"id": "T011", "text": "售后维修寄回后多久能完成检测？", "label": "售后", "reason": "维修进度"},
        {"id": "T012", "text": "我想换大一号尺码，能直接换货吗？", "label": "售后", "reason": "换货售后"},
        {"id": "T013", "text": "优惠券为什么结算时不能使用？", "label": "咨询", "reason": "活动规则咨询"},
        {"id": "T014", "text": "配送地址填错了，现在还能改吗？", "label": "物流", "reason": "配送信息变更"},
        {"id": "T015", "text": "收到的颜色和页面展示不一致，怀疑发错货。", "label": "售后", "reason": "商品异常"},
        {"id": "T016", "text": "我要取消订单并退款。", "label": "退款", "reason": "退款取消"},
        {"id": "T017", "text": "你们平台泄露我的手机号，我要投诉。", "label": "投诉", "reason": "隐私投诉"},
        {"id": "T018", "text": "保修期是多久？电池是否单独保修？", "label": "咨询", "reason": "商品保修咨询"},
        {"id": "T019", "text": "包裹已经到驿站但取件码没有收到。", "label": "物流", "reason": "取件问题"},
        {"id": "T020", "text": "质量太差，要求赔偿。", "label": "投诉", "reason": "质量投诉"},
        {"id": "T021", "text": "退货地址发给我。", "label": "退款", "reason": "退款/退货"},
        {"id": "T022", "text": "商品参数页面看不懂，适合老人用吗？", "label": "咨询", "reason": "使用咨询"},
    ]
    csv_lines = ['id,text,label,reason'] + [f"{t['id']},{t['text']},{t['label']},{t['reason']}" for t in texts]
    (TEXT_DIR / "客服问答意图分类样本.csv").write_text("\n".join(csv_lines), encoding='utf-8')
    (TEXT_DIR / "llm_preference_samples.jsonl").write_text("\n".join(json.dumps({
        "prompt": f"请回答用户问题：{t['text']}",
        "response_a": "您好，已为您记录问题，我会根据订单状态给出下一步处理建议。",
        "response_b": "不知道，自己看订单。",
        "preference": "A",
        "score_dimensions": {"正确性": 4, "完整性": 4, "安全性": 5, "表达质量": 5, "指令遵循": 4},
    }, ensure_ascii=False) for t in texts), encoding='utf-8')

    table_rows = [
        {"id":"O001","order_amount":"268.50","city":"深圳","risk":"正常","remark":"字段完整"},
        {"id":"O002","order_amount":"0","city":"广州","risk":"金额异常","remark":"金额为0"},
        {"id":"O003","order_amount":"99999","city":"上海","risk":"金额异常","remark":"疑似测试订单"},
        {"id":"O004","order_amount":"128.00","city":"","risk":"字段缺失","remark":"城市为空"},
        {"id":"O005","order_amount":"88.90","city":"杭州","risk":"正常","remark":"字段完整"},
        {"id":"O006","order_amount":"88.90","city":"杭州","risk":"重复疑似","remark":"与O005近似重复"},
        {"id":"O007","order_amount":"abc","city":"成都","risk":"类型错误","remark":"金额不是数字"},
        {"id":"O008","order_amount":"320.20","city":"武汉","risk":"正常","remark":"字段完整"},
        {"id":"O009","order_amount":"-12","city":"北京","risk":"金额异常","remark":"负数金额"},
        {"id":"O010","order_amount":"51.30","city":"南京","risk":"正常","remark":"字段完整"},
    ]
    table_csv = IMPORT_DIR / "电商订单表格异常校验样本.csv"
    table_csv.write_text("id,order_amount,city,risk,remark\n" + "\n".join(f"{r['id']},{r['order_amount']},{r['city']},{r['risk']},{r['remark']}" for r in table_rows), encoding='utf-8')
    return construction, traffic, defects, texts, table_rows, table_csv


def _insert_labels(project_id: int, rows: list[tuple]):
    execute_many("""INSERT INTO labels(project_id,name,code,color,label_type,shortcut,required,exclusive,description,positive_example,negative_example,note)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", [(project_id, *r) for r in rows])


def _insert_rules(project_id: int, rows: list[tuple]):
    execute_many("INSERT INTO annotation_rules(project_id,rule_type,title,content,severity) VALUES(?,?,?,?,?)", [(project_id, *r) for r in rows])



IMAGE_BBOX_BY_FILENAME = {
    'helmet_site_01.jpg': [('person',300,245,125,405,.93,'预标注','待确认'),('vest',285,330,140,150,.82,'预标注','待确认'),('helmet',337,245,74,58,.88,'预标注','待确认'),('person',760,275,130,330,.90,'人工','已确认'),('helmet',780,270,72,52,.86,'人工','已确认'),('vehicle',530,120,460,245,.84,'人工','已确认'),('warning_sign',75,405,235,190,.89,'人工','已确认')],
    'municipal_worker_05.jpg': [('person',258,30,76,194,.94,'预标注','待确认'),('vest',258,72,72,96,.88,'预标注','待确认'),('helmet',284,30,36,27,.74,'预标注','待确认'),('vehicle',126,86,126,138,.76,'人工','已确认')],
    'rebar_site_04.jpg': [('person',151,18,94,218,.93,'预标注','待确认'),('helmet',160,14,58,33,.84,'预标注','待确认'),('vest',151,62,74,93,.79,'预标注','待确认'),('person',0,20,64,185,.73,'人工','已确认')],
    'scaffold_site_03.jpg': [('person',612,570,170,390,.92,'预标注','待确认'),('helmet',704,560,70,54,.86,'预标注','待确认'),('vest',600,645,150,170,.82,'预标注','待确认'),('person',1030,570,120,310,.84,'人工','已确认'),('vehicle',1010,485,390,230,.88,'人工','已确认')],
    'tunnel_site_02.jpg': [('person',165,405,230,360,.92,'预标注','待确认'),('helmet',255,365,90,65,.88,'预标注','待确认'),('vest',155,425,230,180,.83,'预标注','待确认'),('person',625,350,180,390,.90,'人工','已确认'),('helmet',685,330,92,62,.87,'人工','已确认'),('warning_sign',1065,490,225,185,.91,'人工','已确认')],
    'city_intersection_day_01.jpg': [('traffic_light',70,165,90,245,.92,'预标注','待确认'),('pedestrian',235,565,55,185,.83,'预标注','待确认'),('pedestrian',620,548,65,180,.82,'预标注','待确认'),('cyclist',1105,520,165,180,.80,'人工','已确认'),('car',430,540,170,92,.88,'人工','已确认'),('bus',760,395,170,150,.83,'人工','已确认'),('road_sign',1150,325,115,82,.86,'人工','已确认')],
    'highway_truck_06.jpg': [('car',30,154,74,48,.86,'预标注','待确认'),('car',113,145,62,45,.84,'预标注','待确认'),('bus',218,55,105,135,.90,'人工','已确认'),('road_sign',325,18,72,54,.88,'人工','已确认')],
    'overhead_intersection_05.jpg': [('car',285,96,92,86,.90,'预标注','待确认'),('cyclist',162,60,42,55,.77,'预标注','待确认'),('cyclist',445,22,56,52,.79,'人工','已确认'),('cyclist',22,90,45,60,.78,'人工','已确认'),('bus',585,0,48,42,.70,'人工','已确认')],
    'rain_expressway_04.jpg': [('car',118,117,70,42,.86,'预标注','待确认'),('car',215,136,56,36,.81,'预标注','待确认'),('car',420,144,62,38,.83,'人工','已确认'),('bus',468,64,70,58,.87,'人工','已确认'),('road_sign',390,24,86,45,.80,'人工','已确认')],
    'rain_night_intersection_02.jpg': [('traffic_light',54,65,70,145,.92,'预标注','待确认'),('bus',635,315,265,180,.90,'预标注','待确认'),('car',265,465,170,105,.83,'预标注','待确认'),('cyclist',855,508,130,170,.79,'人工','已确认'),('pedestrian',1180,492,165,275,.76,'人工','已确认')],
    'school_street_03.jpg': [('bus',535,500,150,110,.88,'预标注','待确认'),('car',620,600,210,110,.88,'人工','已确认'),('cyclist',1070,540,135,235,.80,'预标注','待确认'),('pedestrian',68,615,90,255,.77,'人工','已确认'),('road_sign',1192,310,150,150,.91,'人工','已确认')],
    'bottle_line_06.jpg': [('ok_region',20,90,360,95,.90,'人工','已确认'),('stain',230,92,60,42,.60,'预标注','待确认')],
    'casting_crack_07.jpg': [('crack',255,16,42,195,.95,'预标注','待确认'),('ok_region',48,48,118,88,.84,'人工','已确认')],
    'defective_flange_03.jpg': [('crack',405,575,150,210,.89,'预标注','待确认'),('stain',825,352,165,135,.83,'预标注','待确认'),('stain',1110,665,210,160,.82,'人工','已确认'),('ok_region',170,650,240,210,.86,'人工','已确认')],
    'electronic_shell_04.jpg': [('scratch',50,575,255,145,.87,'预标注','待确认'),('stain',780,745,190,125,.76,'预标注','待确认'),('dent',1040,728,120,95,.70,'人工','已确认'),('ok_region',370,140,220,330,.88,'人工','已确认')],
    'metal_panel_defect_02.jpg': [('dent',270,520,92,76,.86,'预标注','待确认'),('scratch',780,495,220,70,.83,'预标注','待确认'),('stain',465,245,160,120,.78,'人工','已确认'),('ok_region',940,185,300,190,.89,'人工','已确认')],
    'paint_scratch_08.jpg': [('scratch',210,70,235,58,.94,'预标注','待确认'),('ok_region',465,42,95,42,.80,'人工','已确认')],
    'wall_crack_pipe_09.jpg': [('crack',360,0,135,214,.96,'预标注','待确认'),('ok_region',132,18,72,188,.82,'人工','已确认')],
    'warehouse_forklift_01.jpg': [('ok_region',115,265,460,360,.84,'人工','已确认'),('stain',760,710,130,70,.55,'预标注','待确认')],
    'warehouse_pallet_05.jpg': [('ok_region',145,65,120,115,.84,'人工','已确认'),('stain',118,155,58,32,.62,'预标注','待确认')],
}


def _add_image_samples(project_id: int, files: list[tuple[Path, int, int]], prefix: str, label_plan: list[tuple[str, float, float, float, float, float]], assigned='labeler') -> list[int]:
    ids = []
    for idx, (path, w, h) in enumerate(files, start=1):
        status = '预标注待确认' if idx % 4 else '已保存'
        risk = '低置信;小目标' if idx in (2, 7, 12) else ('模糊' if idx in (5, 11, 15) else '')
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,width,height,status,risk_tags,is_ground_truth,is_duplicate,is_low_confidence,rework_count,assigned_to,qc_status)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (project_id, f"{prefix}-{idx:04d}", 'image', path.name, _rel(path), w, h, status, risk, 1 if idx in (2, 9) else 0, 0, 1 if idx in (2, 7, 12) else 0, 1 if idx in (4, 8) else 0, assigned, '待质检' if idx % 3 else '已通过'))
        ids.append(sid)
        rows = IMAGE_BBOX_BY_FILENAME.get(path.name)
        if rows is None:
            rows = [(label, x, y, bw, bh, conf, '预标注' if j < min(3, len(label_plan)) else '人工', '待确认') for j, (label, x, y, bw, bh, conf) in enumerate(label_plan)]
        for label, x, y, bw, bh, conf, src, st in rows:
            execute("""INSERT INTO annotations(sample_id,label,annotation_type,x,y,w,h,confidence,source,status,created_by,comment)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (sid, label, 'bbox', x, y, bw, bh, conf, src, st, assigned, '已按真实演示图片重新校准的目标框'))
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (project_id, project_id))
    return ids


def seed_demo_data() -> None:
    # Fresh packages include a seeded DB. If a user deletes data/app.db, this recreates the richer demo set.
    if fetch_one("SELECT id FROM users LIMIT 1"):
        return
    construction, traffic, defects, text_samples, table_rows, table_csv = _write_demo_files()
    users = [
        ("admin", "admin123", "系统管理员", "管理员"),
        ("labeler", "123456", "标注员A", "标注员"),
        ("reviewer", "123456", "质检员A", "质检员"),
        ("manager", "123456", "项目经理", "项目经理"),
    ]
    execute_many("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)", users)

    p1 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-IMG-2026-001", "安全帽佩戴检测图像数据集", "图像目标检测", "图像", "目标检测框", "训练施工现场安全行为识别模型", "系统管理员", "质检员A", "生产中", "2026-07-15", "v1.2.1", 17, 6, 86.5))
    p2 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-TXT-2026-002", "客服问答意图分类文本数据集", "文本分类", "文本", "文本分类/偏好评价", "训练客服意图分类与回复偏好模型", "系统管理员", "质检员A", "质检中", "2026-07-20", "v0.9.4", 22, 6, 78.2))
    p3 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-TRAFFIC-2026-003", "城市路口交通目标检测数据集", "图像目标检测", "图像", "车辆/行人/信号灯检测", "训练车路协同场景目标识别模型", "系统管理员", "质检员A", "生产中", "2026-08-05", "v0.6.0", 14, 6, 82.4))
    p4 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-QC-2026-004", "工业产品外观缺陷检测数据集", "图像目标检测", "图像", "缺陷框标注", "训练产线外观缺陷自动质检模型", "系统管理员", "质检员A", "返工中", "2026-08-12", "v0.4.2", 12, 5, 74.8))
    p5 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-TABLE-2026-005", "电商订单表格异常校验数据集", "表格样本校验", "表格", "字段质量与异常分类", "训练表格数据清洗与异常识别模型", "系统管理员", "质检员A", "配置中", "2026-08-20", "v0.2.0", 10, 5, 69.5))

    _insert_labels(p1, [
        ("person", "person", "#2563eb", "目标框标签", "1", 1, 0, "施工现场人员目标，需完整贴合身体可见部分。", "安全帽下方完整人体", "车辆或假人模型", "遮挡时仅标可见部分"),
        ("helmet", "helmet", "#f59e0b", "目标框标签", "2", 0, 1, "已佩戴安全帽目标。", "黄色或白色安全帽", "普通帽子或阴影", "helmet 与 no_helmet 互斥"),
        ("no_helmet", "no_helmet", "#ef4444", "目标框标签", "3", 0, 1, "未佩戴安全帽人员头部。", "可见头部无安全帽", "安全帽被遮挡不清", "疑难时标记仲裁"),
        ("vest", "vest", "#22c55e", "目标框标签", "4", 0, 0, "反光背心区域。", "橙色/荧光背心", "普通上衣", "可与person共存"),
        ("vehicle", "vehicle", "#7c3aed", "目标框标签", "5", 0, 0, "施工车辆。", "卡车/叉车/吊车", "手推车", "整车可见部分"),
        ("warning_sign", "warning_sign", "#ec4899", "目标框标签", "6", 0, 0, "警示牌或三角标。", "施工警示牌", "广告牌", "尽量贴近边缘"),
    ])
    _insert_labels(p2, [(name, name, color, "分类标签", str(i+1), 1 if i == 0 else 0, 1, f"客服意图标签：{name}", f"{name}类问题", "非该类主诉求", "主诉求优先原则") for i, (name, color) in enumerate([
        ("退款", "#ef4444"), ("物流", "#2563eb"), ("投诉", "#f97316"), ("咨询", "#22c55e"), ("售后", "#7c3aed"), ("其他", "#64748b")])])
    _insert_labels(p3, [
        ("car", "car", "#2563eb", "目标框标签", "1", 1, 0, "小客车、出租车等机动车。", "完整车身", "远处无法分辨物体", "遮挡时标可见部分"),
        ("bus", "bus", "#7c3aed", "目标框标签", "2", 0, 0, "公交或大型客运车辆。", "公交车/大巴", "货车", "按车身外轮廓"),
        ("pedestrian", "pedestrian", "#22c55e", "目标框标签", "3", 1, 0, "行人目标。", "路口行人", "骑行者", "与cyclist区分"),
        ("cyclist", "cyclist", "#f97316", "目标框标签", "4", 0, 0, "骑行人和自行车整体。", "自行车/电动车骑行者", "单独行人", "人车整体框"),
        ("traffic_light", "traffic_light", "#ef4444", "目标框标签", "5", 0, 0, "交通信号灯。", "红绿灯灯组", "路灯", "灯杆可不纳入"),
        ("road_sign", "road_sign", "#eab308", "目标框标签", "6", 0, 0, "道路标志牌。", "警示/指示牌", "广告牌", "包含可见牌面"),
    ])
    _insert_labels(p4, [
        ("scratch", "scratch", "#ef4444", "目标框标签", "1", 1, 0, "划痕缺陷区域。", "细长线状损伤", "正常纹理", "框住可见划痕主体"),
        ("dent", "dent", "#f59e0b", "目标框标签", "2", 0, 0, "凹陷缺陷。", "局部变形阴影", "光照反射", "需复核光照影响"),
        ("stain", "stain", "#7c3aed", "目标框标签", "3", 0, 0, "污渍/油渍。", "不规则脏污", "背景阴影", "只框污渍区域"),
        ("crack", "crack", "#dc2626", "目标框标签", "4", 1, 0, "裂纹。", "断裂纹路", "划痕", "严重缺陷优先复核"),
        ("ok_region", "ok_region", "#22c55e", "目标框标签", "5", 0, 0, "无缺陷对照区域。", "合格外观", "缺陷区域", "用于正负样本平衡"),
    ])
    _insert_labels(p5, [(name, name, color, "表格质量标签", str(i+1), 0, 1, f"表格异常：{name}", name, "正常字段", "用于字段质检") for i, (name, color) in enumerate([
        ("正常", "#22c55e"), ("字段缺失", "#ef4444"), ("类型错误", "#f97316"), ("金额异常", "#7c3aed"), ("重复疑似", "#2563eb")])])

    _insert_rules(p1, [
        ("图像", "框选边界规则", "框应贴合目标可见边界，截断目标只标可见部分，不允许大面积包含背景。", "高"),
        ("图像", "helmet/no_helmet 互斥规则", "同一头部不可同时标记 helmet 与 no_helmet；无法判断时标疑难。", "高"),
        ("图像", "小目标处理规则", "短边小于10像素且无法判断类别的目标可不标，但需在疑难说明中记录。", "中"),
        ("图像", "重复框规则", "同一目标重复框 IoU 大于0.82时必须合并。", "高"),
    ])
    _insert_rules(p2, [
        ("文本", "主诉求优先规则", "同一句包含多个问题时优先选择用户最核心的诉求。", "高"),
        ("文本", "评价理由规则", "偏好或质量评分必须填写不少于10字的评价理由。", "中"),
        ("文本", "同义文本一致规则", "重复或近似文本应保持相同标签，冲突时进入质检复核。", "高"),
    ])
    _insert_rules(p3, [
        ("图像", "交通目标遮挡规则", "车辆和行人遮挡时按可见外轮廓标注，严重遮挡进入疑难池。", "中"),
        ("图像", "小目标信号灯规则", "信号灯目标很小但可识别时仍需标注。", "高"),
    ])
    _insert_rules(p4, [
        ("图像", "缺陷区域规则", "缺陷框只覆盖可见缺陷，不应包含大面积正常背景。", "高"),
        ("图像", "光照干扰规则", "反光与污渍容易混淆，低置信样本需质检复核。", "中"),
    ])
    _insert_rules(p5, [
        ("表格", "字段完整性规则", "必填字段为空时标记字段缺失，禁止直接进入交付。", "高"),
        ("表格", "数值类型规则", "金额字段必须可解析为非负数，异常值需复核。", "高"),
    ])

    construction_ids = _add_image_samples(p1, construction, 'IMG', [
        ("person", 132, 360, 62, 170, 0.91), ("helmet", 145, 350, 42, 34, 0.87), ("vest", 120, 395, 72, 88, 0.78), ("vehicle", 770, 445, 265, 150, 0.93), ("warning_sign", 475, 458, 110, 100, 0.82)
    ])
    # one visible duplicate sample for duplicate detection: points to an existing high-quality real image.
    dup_path, dup_w, dup_h = construction[0]
    dup_id = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,width,height,status,risk_tags,is_ground_truth,is_duplicate,is_low_confidence,rework_count,assigned_to,qc_status)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (p1, "IMG-DUP-0001", 'image', dup_path.name, _rel(dup_path), dup_w, dup_h, "自动质检异常", "疑似重复", 0, 1, 0, 0, "labeler", "待质检"))
    construction_ids.append(dup_id)
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (p1, p1))

    traffic_ids = _add_image_samples(p3, traffic, 'TRF', [
        ("car", 210, 420, 145, 74, 0.88), ("pedestrian", 120, 408, 48, 116, 0.81), ("traffic_light", 1005, 145, 70, 130, 0.86), ("cyclist", 885, 500, 110, 105, 0.79), ("road_sign", 1058, 330, 115, 72, 0.77)
    ])
    defect_ids = _add_image_samples(p4, defects, 'DEF', [
        ("scratch", 320, 285, 110, 45, 0.74), ("dent", 500, 310, 85, 56, 0.69), ("stain", 660, 245, 95, 62, 0.72), ("ok_region", 245, 260, 130, 130, 0.93)
    ])

    text_ids = []
    for i, item in enumerate(text_samples, start=1):
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,text_content,width,height,status,risk_tags,is_ground_truth,is_duplicate,is_low_confidence,rework_count,assigned_to,qc_status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (p2, item['id'], 'text', f"{item['id']}.txt", _rel(TEXT_DIR / "客服问答意图分类样本.csv"), item['text'], 0, 0, '已保存' if i < 17 else '未开始', '重复' if i == 7 else ('空文本' if i == 5 else ('文本过短' if i == 10 else '')), 1 if i in (1, 6, 11) else 0, 1 if i == 7 else 0, 1 if i in (5, 10) else 0, 0, 'labeler', '待质检' if i % 4 else '已通过'))
        text_ids.append(sid)
        execute("""INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment)
                   VALUES(?,?,?,?,?,?,?,?)""", (sid, item['label'], 'text_class', 0.86, '人工', '已确认', 'labeler', item['reason']))
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (p2, p2))


    # additional text datasets for production-style demonstrations
    finance_texts = [
        {"id": "F001", "text": "昨天转账两万元到对公账户，页面提示处理中，资金什么时候到账？", "label": "转账汇款", "reason": "用户询问转账到账进度"},
        {"id": "F002", "text": "我的信用卡被盗刷三笔境外消费，请马上冻结并协助争议处理。", "label": "盗刷风控", "reason": "高风险盗刷与冻结诉求"},
        {"id": "F003", "text": "APP登录一直提示设备风险，换手机后无法刷脸认证。", "label": "账户安全", "reason": "账户登录与设备风控问题"},
        {"id": "F004", "text": "房贷提前还款需要预约吗？违约金怎么计算？", "label": "贷款咨询", "reason": "贷款提前还款咨询"},
        {"id": "F005", "text": "理财产品显示净值回撤，这个是不是保本的？", "label": "理财咨询", "reason": "理财产品风险咨询"},
        {"id": "F006", "text": "短信验证码不是我本人操作收到的，银行卡是否有风险？", "label": "账户安全", "reason": "疑似异常操作"},
        {"id": "F007", "text": "我想注销二类账户，里面还有几块钱余额怎么处理？", "label": "账户业务", "reason": "账户注销与余额处理"},
        {"id": "F008", "text": "扣了年费但我没收到通知，要求退回。", "label": "费用争议", "reason": "费用扣费争议"},
        {"id": "F009", "text": "为什么我的转账被拦截？对方是我家人不是诈骗。", "label": "风控拦截", "reason": "转账风控拦截申诉"},
        {"id": "F010", "text": "信用卡账单分期利率看不懂，能解释实际年化吗？", "label": "信用卡", "reason": "信用卡分期咨询"},
        {"id": "F011", "text": "", "label": "其他", "reason": "空文本演示"},
        {"id": "F012", "text": "昨天转账两万元到对公账户，页面提示处理中，资金什么时候到账？", "label": "账户业务", "reason": "重复文本标签冲突"},
    ]
    medical_texts = [
        {"id": "M001", "text": "孩子发烧到39度，还伴随咳嗽，应该挂儿科还是急诊？", "label": "儿科导诊", "reason": "儿童发热导诊"},
        {"id": "M002", "text": "体检报告显示血糖偏高，想预约内分泌科复查。", "label": "慢病复诊", "reason": "血糖异常复查"},
        {"id": "M003", "text": "膝盖运动后疼痛，走楼梯明显，需要看骨科吗？", "label": "骨科咨询", "reason": "关节疼痛导诊"},
        {"id": "M004", "text": "皮肤突然起红疹并瘙痒，可能是过敏吗？", "label": "皮肤过敏", "reason": "皮肤症状咨询"},
        {"id": "M005", "text": "昨晚胸口闷痛十分钟，现在还有点气短。", "label": "急症风险", "reason": "胸痛气短为高风险症状"},
        {"id": "M006", "text": "医生开的药吃完后胃不舒服，可以自行停药吗？", "label": "用药咨询", "reason": "用药不良反应咨询"},
        {"id": "M007", "text": "孕12周需要做哪些产检？NT检查要预约吗？", "label": "产检咨询", "reason": "孕期产检咨询"},
        {"id": "M008", "text": "晚上睡不着已经两周，白天注意力很差。", "label": "心理睡眠", "reason": "睡眠与心理健康问题"},
        {"id": "M009", "text": "血压160/100，头晕，我要不要马上去医院？", "label": "急症风险", "reason": "高血压伴头晕风险"},
        {"id": "M010", "text": "牙龈肿痛三天，吃东西会出血。", "label": "口腔咨询", "reason": "口腔科导诊"},
        {"id": "M011", "text": "膝盖运动后疼痛，走楼梯明显，需要看骨科吗？", "label": "运动康复", "reason": "重复文本标签冲突"},
        {"id": "M012", "text": "胸", "label": "急症风险", "reason": "文本过短演示"},
    ]
    finance_csv = TEXT_DIR / "金融客服风险意图样本.csv"
    finance_csv.write_text('id,text,label,reason\n' + '\n'.join(f"{t['id']},{t['text']},{t['label']},{t['reason']}" for t in finance_texts), encoding='utf-8')
    medical_csv = TEXT_DIR / "医疗导诊意图样本.csv"
    medical_csv.write_text('id,text,label,reason\n' + '\n'.join(f"{t['id']},{t['text']},{t['label']},{t['reason']}" for t in medical_texts), encoding='utf-8')

    p6 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-FIN-2026-006", "金融客服风险意图文本数据集", "文本分类", "文本", "风险意图分类/实体抽取", "训练金融客服风险识别与工单分流模型", "系统管理员", "质检员A", "生产中", "2026-08-28", "v0.3.0", 12, 8, 81.6))
    _insert_labels(p6, [(name, name, color, "分类标签", str(i+1), 1 if i == 0 else 0, 1, f"金融意图标签：{name}", f"{name}类问题", "非该类主诉求", "风险优先，涉及盗刷/验证码/拦截需复核") for i, (name, color) in enumerate([
        ("账户安全", "#ef4444"), ("转账汇款", "#2563eb"), ("盗刷风控", "#dc2626"), ("贷款咨询", "#7c3aed"), ("理财咨询", "#22c55e"), ("费用争议", "#f97316"), ("信用卡", "#06b6d4"), ("其他", "#64748b")])])
    _insert_rules(p6, [
        ("文本", "金融风险优先规则", "盗刷、验证码异常、转账拦截等安全事件优先标为风险类，不可仅标普通咨询。", "高"),
        ("文本", "金额与账户实体规则", "金额、账户类型、转账对象等实体应完整标注，用于后续风控模型训练。", "中"),
    ])
    finance_ids = []
    for i, item in enumerate(finance_texts, start=1):
        risk = '空文本' if item['text'] == '' else ('重复' if i == 12 else ('高风险' if item['label'] in ('盗刷风控','账户安全','风控拦截') else ''))
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,text_content,width,height,status,risk_tags,is_ground_truth,is_duplicate,is_low_confidence,rework_count,assigned_to,qc_status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (p6, item['id'], 'text', f"{item['id']}.txt", _rel(finance_csv), item['text'], 0, 0, '已保存' if i <= 8 else '未开始', risk, 1 if i in (2,5) else 0, 1 if i == 12 else 0, 1 if risk else 0, 0, 'labeler', '待质检' if risk else '已通过'))
        finance_ids.append(sid)
        execute("""INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment)
                   VALUES(?,?,?,?,?,?,?,?)""", (sid, item['label'], 'text_class', 0.84, '人工', '已确认', 'labeler', item['reason']))
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (p6, p6))

    p7 = execute("""INSERT INTO dataset_projects(code,name,project_type,data_type,task_type,training_goal,owner,reviewer,status,deadline,version_no,sample_count,label_count,health_score)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("DS-MED-2026-007", "医疗导诊问答意图文本数据集", "文本分类", "文本", "导诊意图/风险分级", "训练医疗导诊分流与高风险提示模型", "系统管理员", "质检员A", "质检中", "2026-09-03", "v0.2.5", 12, 8, 76.4))
    _insert_labels(p7, [(name, name, color, "分类标签", str(i+1), 1 if i == 0 else 0, 1, f"医疗导诊标签：{name}", f"{name}类问题", "非该类主诉求", "急症风险优先，避免误导诊断") for i, (name, color) in enumerate([
        ("急症风险", "#dc2626"), ("儿科导诊", "#2563eb"), ("慢病复诊", "#22c55e"), ("骨科咨询", "#7c3aed"), ("皮肤过敏", "#f97316"), ("用药咨询", "#06b6d4"), ("产检咨询", "#ec4899"), ("其他", "#64748b")])])
    _insert_rules(p7, [
        ("文本", "医疗安全规则", "胸痛、气短、高热、血压异常等高风险症状应优先标记急症风险，并进入质检复核。", "高"),
        ("文本", "非诊断表达规则", "样本评价理由应避免给出确定诊断，只标注意图、风险等级和导诊建议。", "高"),
    ])
    medical_ids = []
    for i, item in enumerate(medical_texts, start=1):
        risk = '高风险' if item['label'] == '急症风险' else ('重复' if i == 11 else ('文本过短' if i == 12 else ''))
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,text_content,width,height,status,risk_tags,is_ground_truth,is_duplicate,is_low_confidence,rework_count,assigned_to,qc_status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (p7, item['id'], 'text', f"{item['id']}.txt", _rel(medical_csv), item['text'], 0, 0, '已保存' if i <= 7 else '未开始', risk, 1 if i in (1,5) else 0, 1 if i == 11 else 0, 1 if risk else 0, 0, 'labeler', '待质检' if risk else '已通过'))
        medical_ids.append(sid)
        execute("""INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment)
                   VALUES(?,?,?,?,?,?,?,?)""", (sid, item['label'], 'text_class', 0.82, '人工', '已确认', 'labeler', item['reason']))
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (p7, p7))

    execute_many("""INSERT INTO quality_issues(sample_id,annotation_id,issue_type,severity,rule_name,position_text,suggestion,status)
                   VALUES(?,?,?,?,?,?,?,?)""", [
        (finance_ids[1], None, "疑似盗刷高风险", "高", "FinanceFraudRisk", "F002", "优先冻结和争议处理，需人工复核", "待处理"),
        (finance_ids[10], None, "文本为空", "高", "EmptyText", "F011", "删除或补充原始文本", "待处理"),
        (finance_ids[11], None, "重复文本标签冲突", "高", "DuplicateTextConflict", "F001/F012", "统一转账主诉求标签", "待处理"),
        (medical_ids[4], None, "急症风险提示", "高", "MedicalSafety", "M005", "胸痛气短应进入高风险复核", "待处理"),
        (medical_ids[10], None, "重复文本标签冲突", "中", "DuplicateTextConflict", "M003/M011", "统一骨科/康复主诉求标签", "待处理"),
        (medical_ids[11], None, "文本过短", "中", "TooShort", "M012", "补充上下文或剔除", "待处理"),
    ])

    table_ids = []
    for i, row in enumerate(table_rows, start=1):
        sid = execute("""INSERT INTO samples(project_id,sample_code,sample_type,filename,file_path,text_content,status,risk_tags,is_duplicate,is_low_confidence,assigned_to,qc_status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (p5, row['id'], 'table', table_csv.name, _rel(table_csv), json.dumps(row, ensure_ascii=False), '已保存' if row['risk'] == '正常' else '自动质检异常', row['risk'], 1 if row['risk']=='重复疑似' else 0, 1 if row['risk']!='正常' else 0, 'labeler', '待质检'))
        table_ids.append(sid)
        execute("INSERT INTO annotations(sample_id,label,annotation_type,confidence,source,status,created_by,comment) VALUES(?,?,?,?,?,?,?,?)", (sid, row['risk'], 'table_quality', 0.82, '规则引擎', '已确认', 'system', row['remark']))
    execute("UPDATE dataset_projects SET sample_count=(SELECT COUNT(*) FROM samples WHERE project_id=?) WHERE id=?", (p5, p5))

    # quality issues across richer datasets
    issue_rows = [
        (construction_ids[1], None, "小目标疑似漏标", "中", "SmallObjectMissing", "右侧工人头部区域", "放大后确认安全帽目标是否需要补标", "待处理"),
        (construction_ids[3], None, "标注框越界", "高", "BBoxBoundary", "左侧 person 框越界", "调整框到图像内", "待处理"),
        (construction_ids[7], None, "同目标重复框", "高", "DuplicateIoU", "helmet 重复框", "删除重复框并保留置信较高目标", "待处理"),
        (construction_ids[10], None, "图片模糊", "中", "BlurImage", "全图", "建议人工复核是否可用于训练", "已确认"),
        (dup_id, None, "重复图片", "高", "DuplicateImage", "与 IMG-0003 完全重复", "确认是否剔除或只保留一张", "待处理"),
        (traffic_ids[3], None, "雨天低能见度", "中", "LowVisibility", "全图", "优先复核行人和信号灯", "待处理"),
        (traffic_ids[6], None, "行人/骑行者类别分歧", "中", "ClassConflict", "画面右侧骑行者", "按cyclist整体框处理", "待处理"),
        (defect_ids[2], None, "光照疑似误检", "中", "ReflectionNoise", "产品中部", "复核污渍和反光边界", "待处理"),
        (defect_ids[4], None, "缺陷框过大", "高", "DefectBBoxTooLarge", "scratch 框", "缩小到缺陷可见区域", "待处理"),
        (text_ids[4], None, "文本为空", "高", "EmptyText", "T005", "删除或补充原始文本", "待处理"),
        (text_ids[6], None, "重复文本标签不一致", "高", "DuplicateTextConflict", "T001/T007", "统一主诉求标签或进入仲裁", "待处理"),
        (text_ids[9], None, "文本过短", "中", "TooShort", "T010", "补充上下文或剔除样本", "待处理"),
        (table_ids[1], None, "金额为零", "中", "AmountZero", "O002.order_amount", "确认是否真实促销订单", "待处理"),
        (table_ids[6], None, "金额字段类型错误", "高", "AmountType", "O007.order_amount", "需要转换或剔除", "待处理"),
        (table_ids[8], None, "负数金额", "高", "NegativeAmount", "O009.order_amount", "进入人工复核", "待处理"),
    ]
    execute_many("""INSERT INTO quality_issues(sample_id,annotation_id,issue_type,severity,rule_name,position_text,suggestion,status)
                   VALUES(?,?,?,?,?,?,?,?)""", issue_rows)

    reworks = [
        ("RW-202606-0001", construction_ids[3], p1, "labeler", "reviewer", "标注框越界/漏标", "person 框越界且右侧 helmet 漏标 1 处。", "补充右侧安全帽标注，调整左侧 person 框边界，提交前重新自检。", (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'), "待返工", "", ""),
        ("RW-202606-0002", construction_ids[7], p1, "labeler", "reviewer", "重复框", "helmet 与 no_helmet 存在混淆且重复框。", "保留正确类别，删除重复框，填写疑难原因。", (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'), "返工中", "", ""),
        ("RW-202606-0003", defect_ids[4], p4, "labeler", "reviewer", "缺陷框过大", "scratch框包含大量正常背景。", "缩小到缺陷可见区域，并补充dent疑难说明。", (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), "待返工", "", ""),
    ]
    execute_many("""INSERT INTO rework_tasks(rework_code,sample_id,project_id,labeler,reviewer,issue_type,issue_desc,requirement,deadline,status,second_review,arbitration_result)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", reworks)

    gt_rows = [
        (construction_ids[1], {"labels": ["person", "helmet", "vest", "vehicle"]}, 92.5, "通过：主要目标齐全，小目标建议复核。", "admin"),
        (construction_ids[8], {"labels": ["person", "helmet", "warning_sign"]}, 88.0, "轻微漏标风险，需抽检。", "admin"),
        (traffic_ids[1], {"labels": ["car", "pedestrian", "traffic_light"]}, 90.2, "交通要素标注完整。", "admin"),
        (defect_ids[2], {"labels": ["scratch", "stain"]}, 76.5, "缺陷边界需复核。", "admin"),
        (text_ids[0], {"label": "退款"}, 95.0, "标准答案一致。", "admin"),
    ]
    for sid, ans, score, conclusion, user in gt_rows:
        execute("INSERT INTO ground_truth(sample_id,answer_json,score,conclusion,created_by) VALUES(?,?,?,?,?)", (sid, json.dumps(ans, ensure_ascii=False), score, conclusion, user))

    execute_many("""INSERT INTO consensus_results(project_id,sample_id,worker_a,worker_b,iou_score,label_agreement,diff_summary,need_arbitration)
                   VALUES(?,?,?,?,?,?,?,?)""", [
        (p1, construction_ids[1], "labeler", "labeler_b", 0.87, 0.92, "安全帽框位置轻微偏移。", 0),
        (p1, construction_ids[3], "labeler", "labeler_b", 0.61, 0.68, "person 越界框和 helmet/no_helmet 类别分歧。", 1),
        (p2, text_ids[6], "labeler", "labeler_b", 0.0, 0.58, "退款/售后主诉求分歧。", 1),
        (p3, traffic_ids[6], "labeler", "labeler_c", 0.72, 0.74, "cyclist 与 pedestrian 标注范围不一致。", 1),
        (p4, defect_ids[4], "labeler", "labeler_c", 0.55, 0.70, "scratch/dent 边界分歧明显。", 1),
    ])

    versions = [
        (p1, "v1.2.1", 17, 12, 84.6, 0.8, 0.1, 0.1, "待冻结", "admin", "", "安全帽数据集候选交付版本", "新增4张施工场景样本，保留1张重复样本用于体检演示。"),
        (p2, "v0.9.4", 22, 14, 72.0, 0.8, 0.1, 0.1, "编辑中", "admin", "", "客服意图文本数据集内测版", "补充发票、维修、隐私投诉等长尾意图。"),
        (p3, "v0.6.0", 14, 8, 78.5, 0.8, 0.1, 0.1, "待冻结", "admin", "", "交通路口检测样本版本", "新增雨天低能见度样本。"),
        (p4, "v0.4.2", 12, 5, 58.0, 0.7, 0.15, 0.15, "返工中", "admin", "", "工业缺陷检测样本版本", "缺陷框边界质量不稳定，需返工。"),
        (p5, "v0.2.0", 10, 4, 60.0, 0.7, 0.15, 0.15, "编辑中", "admin", "", "表格异常校验样本版本", "用于演示字段缺失、金额异常和重复疑似。"),
        (p6, "v0.3.0", 12, 7, 70.5, 0.8, 0.1, 0.1, "编辑中", "admin", "", "金融客服风险意图文本样本版本", "新增盗刷风控、账户安全、转账拦截等高风险文本。"),
        (p7, "v0.2.5", 12, 6, 68.0, 0.8, 0.1, 0.1, "质检中", "admin", "", "医疗导诊问答意图文本样本版本", "新增急症风险、儿科导诊、用药咨询等安全敏感文本。"),
    ]
    execute_many("""INSERT INTO dataset_versions(project_id,version_no,sample_total,passed_total,qc_pass_rate,train_ratio,val_ratio,test_ratio,status,frozen_by,frozen_at,description,diff_from_prev)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", versions)

    demo_report = DOCS_DIR / "标注质量报告示例.md"
    demo_report.write_text("# 人工智能模型训练样本智能标注与质量校验管理软件 - 标注质量报告示例\n\n当前演示库包含安全帽、交通路口、工业缺陷、客服文本、金融风险文本、医疗导诊文本和表格异常 7 类项目；质量问题覆盖漏标、重复、越界、模糊、类别分歧、文本为空、表格字段异常等真实生产场景。\n", encoding='utf-8')
    execute("INSERT INTO reports(project_id,report_type,title,file_path,conclusion,created_by) VALUES(?,?,?,?,?,?)", (p1, "标注质量报告", "多项目演示数据质量报告", _rel(demo_report), "建议复核后交付", "admin"))

    execute_many("INSERT INTO operation_logs(username,action,detail) VALUES(?,?,?)", [
        ("admin", "初始化系统", "创建7个演示项目、标签、样本、预标注和质检记录"),
        ("labeler", "保存标注", "完成 IMG-0004 返工样本的首次修正"),
        ("reviewer", "生成返工", "将 IMG-0004 与 DEF-0005 退回返工并填写质检意见"),
        ("manager", "查看驾驶舱", "检查交通与工业质检项目交付风险"),
    ])
