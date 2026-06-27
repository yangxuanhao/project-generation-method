from pathlib import Path

APP_NAME = "人工智能模型训练样本智能标注与质量校验管理软件"
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
DEMO_DIR = DATA_DIR / "demo"
IMAGE_DIR = DEMO_DIR / "images"
TEXT_DIR = DEMO_DIR / "texts"
ANNOTATION_DIR = DEMO_DIR / "annotations"
IMPORT_DIR = DEMO_DIR / "imports"
EXPORT_DIR = DEMO_DIR / "exports"
DOCS_DIR = BASE_DIR / "docs"

for p in [DATA_DIR, DEMO_DIR, IMAGE_DIR, TEXT_DIR, ANNOTATION_DIR, IMPORT_DIR, EXPORT_DIR, DOCS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
