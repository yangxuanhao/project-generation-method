from pathlib import Path


def load_stylesheet() -> str:
    path = Path(__file__).resolve().parent / "styles.qss"
    return path.read_text(encoding="utf-8") if path.exists() else ""
