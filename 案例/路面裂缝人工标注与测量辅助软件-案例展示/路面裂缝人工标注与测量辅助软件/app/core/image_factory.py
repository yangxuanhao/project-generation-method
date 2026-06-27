from __future__ import annotations

from pathlib import Path
from PyQt6.QtGui import QImage, QPainter, QColor, QPen
from PyQt6.QtCore import QPointF, Qt


def ensure_sample_images(sample_dir: Path):
    sample_dir.mkdir(parents=True, exist_ok=True)
    if list(sample_dir.glob('*.png')):
        return
    for index in range(1, 3):
        create_fallback_sample(sample_dir / f'fallback_sample_{index}.png', index)


def create_fallback_sample(path: Path, seed: int):
    w, h = 1280, 820
    image = QImage(w, h, QImage.Format.Format_RGB32)
    image.fill(QColor(144, 148, 150))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i in range(2200):
        x = (i * 97 + seed * 31) % w
        y = (i * 53 + seed * 71) % h
        g = 120 + ((i * 17) % 45)
        painter.setPen(QPen(QColor(g, g, g), 1))
        painter.drawPoint(x, y)
    painter.setPen(QPen(QColor(40, 40, 40), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    cracks = [
        [(160, 190), (320, 240), (450, 280), (620, 330), (920, 380)],
        [(740, 90), (710, 210), (760, 360), (720, 520), (770, 710)],
    ]
    for line in cracks:
        for a, b in zip(line[:-1], line[1:]):
            painter.drawLine(QPointF(*a), QPointF(*b))
    painter.end()
    image.save(str(path))
