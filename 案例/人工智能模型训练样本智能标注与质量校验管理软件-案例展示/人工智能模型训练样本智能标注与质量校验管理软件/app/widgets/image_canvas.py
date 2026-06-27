from __future__ import annotations
from pathlib import Path
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QPen, QColor, QBrush, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from app.core.config import BASE_DIR


class ImageCanvas(QWidget):
    bbox_created = pyqtSignal(dict)
    bbox_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 360)
        self.pixmap: QPixmap | None = None
        self.image_path = ''
        self.bboxes: list[dict] = []
        self.zoom = 0.65
        self.pan = QPointF(30, 30)
        self.mode = 'draw'
        self.current_label = 'person'
        self.dragging = False
        self.drawing = False
        self.start_image = QPointF()
        self.end_image = QPointF()
        self.show_prelabel = True
        self.show_quality = True
        self.show_gt = False
        self.selected_id: int | None = None
        self.mouse_pos_img = QPointF()
        self.setMouseTracking(True)

    def load_image(self, path: str, bboxes: list[dict] | None = None):
        self.image_path = path
        img_path = Path(path) if path else Path()
        if path and not img_path.exists() and not img_path.is_absolute():
            img_path = BASE_DIR / path
        self.pixmap = QPixmap(str(img_path)) if path and img_path.exists() else None
        self.bboxes = [dict(b) for b in (bboxes or [])]
        self.selected_id = self.bboxes[0]['id'] if self.bboxes else None
        if self.pixmap and not self.pixmap.isNull():
            self.fit_to_window()
        self.update()

    def fit_to_window(self):
        if not self.pixmap or self.pixmap.isNull():
            return
        sx = max(0.1, (self.width() - 80) / self.pixmap.width())
        sy = max(0.1, (self.height() - 80) / self.pixmap.height())
        self.zoom = min(sx, sy)
        self.pan = QPointF((self.width() - self.pixmap.width() * self.zoom) / 2, (self.height() - self.pixmap.height() * self.zoom) / 2)

    def image_to_screen(self, p: QPointF) -> QPointF:
        return QPointF(self.pan.x() + p.x() * self.zoom, self.pan.y() + p.y() * self.zoom)

    def screen_to_image(self, p: QPointF) -> QPointF:
        return QPointF((p.x() - self.pan.x()) / self.zoom, (p.y() - self.pan.y()) / self.zoom)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#101827'))
        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor('#cbd5e1'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '请选择样本或导入图片')
            return
        target = QRectF(self.pan.x(), self.pan.y(), self.pixmap.width() * self.zoom, self.pixmap.height() * self.zoom)
        painter.drawPixmap(target, self.pixmap, QRectF(0, 0, self.pixmap.width(), self.pixmap.height()))
        # grid overlay
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        step = max(40, int(100 * self.zoom))
        x = target.left()
        while x < target.right():
            painter.drawLine(int(x), int(target.top()), int(x), int(target.bottom()))
            x += step
        y = target.top()
        while y < target.bottom():
            painter.drawLine(int(target.left()), int(y), int(target.right()), int(y))
            y += step
        for box in self.bboxes:
            if box.get('source') == '预标注' and not self.show_prelabel:
                continue
            if box.get('source') == 'Ground Truth' and not self.show_gt:
                continue
            self._draw_box(painter, box)
        if self.drawing:
            self._draw_temp(painter)
        # status HUD
        painter.setPen(QColor('#e2e8f0'))
        painter.setFont(QFont('Microsoft YaHei', 10))
        painter.drawText(12, self.height() - 16, f"缩放 {self.zoom:.2f}x | 坐标 x={self.mouse_pos_img.x():.0f}, y={self.mouse_pos_img.y():.0f} | 当前标签 {self.current_label}")

    def _draw_box(self, painter: QPainter, box: dict):
        color = QColor(box.get('color') or ('#f59e0b' if box.get('source') == '预标注' else '#22c55e'))
        if box.get('status') == '待确认':
            color = QColor('#f97316')
        if box.get('id') == self.selected_id:
            color = QColor('#38bdf8')
        if box.get('issue') and self.show_quality:
            color = QColor('#ef4444')
        sx = self.pan.x() + float(box['x']) * self.zoom
        sy = self.pan.y() + float(box['y']) * self.zoom
        sw = float(box['w']) * self.zoom
        sh = float(box['h']) * self.zoom
        pen = QPen(color, 2.5 if box.get('id') == self.selected_id else 2)
        if box.get('source') == '预标注':
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 28)))
        painter.drawRect(QRectF(sx, sy, sw, sh))
        painter.setBrush(QBrush(color))
        text = f"{box.get('label','?')} {float(box.get('confidence', 1))*100:.0f}% {box.get('source','')}"
        font = QFont('Microsoft YaHei', 9)
        painter.setFont(font)
        tw = max(70, len(text) * 8)
        painter.drawRoundedRect(QRectF(sx, max(0, sy - 24), tw, 22), 5, 5)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(QRectF(sx + 5, max(0, sy - 23), tw - 8, 22), Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_temp(self, painter: QPainter):
        a = self.image_to_screen(self.start_image)
        b = self.image_to_screen(self.end_image)
        rect = QRectF(a, b).normalized()
        painter.setPen(QPen(QColor('#60a5fa'), 2, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(QColor(96, 165, 250, 32)))
        painter.drawRect(rect)

    def wheelEvent(self, event):
        old = self.screen_to_image(QPointF(event.position()))
        factor = 1.15 if event.angleDelta().y() > 0 else 0.87
        self.zoom = min(5.0, max(0.1, self.zoom * factor))
        new = self.image_to_screen(old)
        self.pan += QPointF(event.position()) - new
        self.update()

    def mousePressEvent(self, event):
        p = QPointF(event.position())
        img_p = self.screen_to_image(p)
        if event.button() == Qt.MouseButton.LeftButton and self.mode == 'draw':
            hit = self._hit_test(img_p)
            if hit is not None:
                self.selected_id = hit
                self.bbox_selected.emit(hit)
            else:
                self.drawing = True
                self.start_image = img_p
                self.end_image = img_p
        else:
            self.dragging = True
            self._last_pos = p
        self.update()

    def mouseMoveEvent(self, event):
        p = QPointF(event.position())
        self.mouse_pos_img = self.screen_to_image(p)
        if self.drawing:
            self.end_image = self.mouse_pos_img
        elif self.dragging:
            self.pan += p - self._last_pos
            self._last_pos = p
        self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing:
            rect = QRectF(self.start_image, self.end_image).normalized()
            if rect.width() > 5 and rect.height() > 5:
                box = {'label': self.current_label, 'x': rect.x(), 'y': rect.y(), 'w': rect.width(), 'h': rect.height(), 'confidence': 1.0, 'source': '人工', 'status': '已确认'}
                self.bbox_created.emit(box)
            self.drawing = False
        self.dragging = False
        self.update()

    def _hit_test(self, p: QPointF) -> int | None:
        for box in reversed(self.bboxes):
            rect = QRectF(float(box['x']), float(box['y']), float(box['w']), float(box['h']))
            if rect.contains(p):
                return int(box.get('id'))
        return None

    def select_box(self, annotation_id: int):
        self.selected_id = annotation_id
        self.update()

    def set_current_label(self, label: str):
        self.current_label = label
        self.update()
