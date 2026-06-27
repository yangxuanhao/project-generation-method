from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QMessageBox, QInputDialog
from PyQt6.QtGui import QPainter, QPixmap, QPen, QColor, QBrush, QFont, QImage, QPolygonF
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QRectF
from app.core.models import CrackObject, CrackRegion
from app.core.geometry import polyline_length_real, smooth_polyline, nearest_point_index, distance
from app.core.calibration import ImageCalibrationEngine
from app.core.width_gauge import CrackWidthGauge
from app.core.region_analyzer import CrackRegionAnalyzer
from app.core.severity import CrackSeverityEvaluator


class CrackAnnotationCanvas(QWidget):
    canvas_changed = pyqtSignal()
    request_save = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(780, 540)
        self.setMouseTracking(True)
        self.scale = 0.75
        self.offset = QPointF(30, 30)
        self.panning = False
        self.last_mouse = QPointF(0, 0)
        self.dragging_node = None
        self.hover_world = None
        self.pixmap = QPixmap()
        self.qimage = QImage()
        self.calibration_points = []
        self.state.task_changed.connect(self.reload_task_image)
        self.state.selection_changed.connect(self.update)
        self.state.mode_changed.connect(lambda _: self.update())
        self.state.view_flags_changed.connect(self.update)

    def reload_task_image(self):
        task = self.state.current_task
        if task and task.image_path:
            self.pixmap = QPixmap(task.image_path)
            self.qimage = self.pixmap.toImage() if not self.pixmap.isNull() else QImage()
        else:
            self.pixmap = QPixmap()
            self.qimage = QImage()
        self.fit_image(); self.update()

    def fit_image(self):
        if self.pixmap.isNull():
            self.scale = 1.0; self.offset = QPointF(20, 20); return
        sw = max(1, self.width() - 80); sh = max(1, self.height() - 80)
        self.scale = min(sw / self.pixmap.width(), sh / self.pixmap.height(), 1.0)
        self.offset = QPointF((self.width() - self.pixmap.width() * self.scale) / 2, (self.height() - self.pixmap.height() * self.scale) / 2)

    def world_to_screen(self, p):
        return QPointF(p[0] * self.scale + self.offset.x(), p[1] * self.scale + self.offset.y())

    def screen_to_world(self, pos):
        return ((pos.x() - self.offset.x()) / self.scale, (pos.y() - self.offset.y()) / self.scale)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#eef2f7'))
        if self.pixmap.isNull():
            painter.setPen(QColor('#7f93ab'))
            painter.setFont(QFont('Microsoft YaHei', 18, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '请在影像任务舱导入路面影像或打开样例影像')
            return
        shadow_rect = QRectF(self.offset.x() + 6, self.offset.y() + 6, self.pixmap.width() * self.scale, self.pixmap.height() * self.scale)
        painter.fillRect(shadow_rect, QColor(150, 163, 184, 55))
        painter.drawPixmap(int(self.offset.x()), int(self.offset.y()), int(self.pixmap.width() * self.scale), int(self.pixmap.height() * self.scale), self.pixmap)
        if self.state.show_reference_grid:
            self._draw_image_grid(painter)
        painter.setPen(QPen(QColor('#c9d3df'), 1))
        painter.drawRect(QRectF(self.offset.x(), self.offset.y(), self.pixmap.width() * self.scale, self.pixmap.height() * self.scale))
        self._draw_overlays(painter)
        self._draw_hud(painter)
        if self.state.show_scale_ruler:
            self._draw_scale_ruler(painter)

    def _draw_image_grid(self, painter):
        if self.pixmap.isNull():
            return
        alpha = int(255 * max(0, min(100, self.state.reference_grid_opacity)) / 100)
        if alpha <= 0:
            return
        left = self.offset.x()
        top = self.offset.y()
        right = left + self.pixmap.width() * self.scale
        bottom = top + self.pixmap.height() * self.scale
        step = max(30, int(200 * self.scale))
        painter.save()
        painter.setClipRect(QRectF(left, top, right - left, bottom - top))
        painter.setPen(QPen(QColor(46, 125, 255, alpha), 1, Qt.PenStyle.DashLine))
        x = left
        while x <= right:
            painter.drawLine(int(x), int(top), int(x), int(bottom))
            x += step
        y = top
        while y <= bottom:
            painter.drawLine(int(left), int(y), int(right), int(y))
            y += step
        painter.restore()

    def _severity_color(self, severity, selected=False):
        if selected:
            return QColor('#1677ff')
        opacity = int(255 * max(15, min(100, self.state.overlay_line_opacity)) / 100)
        color = {
            '轻微': QColor('#31b057'),
            '一般': QColor('#f1aa1f'),
            '较重': QColor('#f07c32'),
            '严重': QColor('#df4b63'),
            '未评估': QColor('#7b8da1'),
        }.get(severity, QColor('#7b8da1'))
        color.setAlpha(opacity)
        return color

    def _draw_overlays(self, painter):
        task = self.state.current_task
        if not task:
            return
        # 候选裂缝
        for candidate in task.candidates:
            if candidate.status != '待确认' or len(candidate.points) < 2:
                continue
            painter.setPen(QPen(QColor('#8c5bff'), 2, Qt.PenStyle.DashLine))
            pts = [self.world_to_screen(p) for p in candidate.points]
            for a, b in zip(pts[:-1], pts[1:]):
                painter.drawLine(a, b)
            center = pts[len(pts)//2]
            painter.setPen(QColor('#6d46cb'))
            painter.drawText(center + QPointF(5, -5), f'疑似 {candidate.score:.0f}')
        # 网裂区域
        for region in task.regions:
            if len(region.polygon_points) < 3:
                continue
            poly = QPolygonF([self.world_to_screen(p) for p in region.polygon_points])
            painter.setBrush(QBrush(QColor(255, 196, 64, 55)))
            painter.setPen(QPen(self._severity_color(region.severity), 2, Qt.PenStyle.DashLine))
            painter.drawPolygon(poly)
            c = poly.boundingRect().center()
            painter.setPen(QColor('#7d5b00'))
            painter.drawText(c, f'{region.region_id}\n{region.area_m2:.2f}㎡ {region.severity}')
        # 正式裂缝
        for crack in task.cracks:
            if len(crack.points) < 2:
                continue
            selected = crack.crack_id == self.state.selected_crack_id
            color = self._severity_color(crack.severity, selected)
            width = 5 if selected else 3
            if crack.locked:
                pen = QPen(color, width, Qt.PenStyle.SolidLine)
            elif crack.review_status == '已退回':
                pen = QPen(QColor('#df4b63'), width, Qt.PenStyle.DashDotLine)
            else:
                pen = QPen(color, width, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            pts = [self.world_to_screen(p) for p in crack.points]
            for a, b in zip(pts[:-1], pts[1:]):
                painter.drawLine(a, b)
            painter.setBrush(QBrush(QColor('white')))
            for pt in pts:
                painter.setPen(QPen(color, 2))
                painter.drawEllipse(pt, 4, 4)
            mid = pts[len(pts)//2]
            # 只有选中裂缝才显示编号标签和宽度文字，避免自动识别后标签铺满画面。
            if selected:
                painter.setPen(QPen(QColor('#ffffff'), 1)); painter.setBrush(QBrush(color))
                painter.drawRoundedRect(int(mid.x()+8), int(mid.y()-28), 112, 24, 8, 8)
                painter.setPen(QColor('white'))
                painter.drawText(int(mid.x()+14), int(mid.y()-11), crack.crack_id[-8:])
                painter.setPen(QPen(QColor('#4fb8d9'), 2))
                for sample in crack.width_samples:
                    a, b = self.world_to_screen(sample.p1), self.world_to_screen(sample.p2)
                    painter.drawLine(a, b); painter.drawEllipse(a, 3, 3); painter.drawEllipse(b, 3, 3)
                    mid2 = QPointF((a.x()+b.x())/2, (a.y()+b.y())/2)
                    painter.drawText(mid2 + QPointF(4, -4), f'{sample.width_mm:.1f}mm')
        # 当前临时折线
        if self.state.temporary_points:
            painter.setPen(QPen(QColor('#1677ff'), 2, Qt.PenStyle.DashLine))
            pts = [self.world_to_screen(p) for p in self.state.temporary_points]
            for a, b in zip(pts[:-1], pts[1:]):
                painter.drawLine(a, b)
            painter.setBrush(QBrush(QColor('#1677ff')))
            for pt in pts:
                painter.drawEllipse(pt, 4, 4)
        if self.state.region_pending_points:
            painter.setPen(QPen(QColor('#ffb703'), 2, Qt.PenStyle.DashLine))
            pts = [self.world_to_screen(p) for p in self.state.region_pending_points]
            for a, b in zip(pts[:-1], pts[1:]):
                painter.drawLine(a, b)
            for pt in pts:
                painter.drawEllipse(pt, 4, 4)
        if self.calibration_points:
            painter.setPen(QPen(QColor('#0f172a'), 2))
            pts = [self.world_to_screen(p) for p in self.calibration_points]
            for p in pts: painter.drawEllipse(p, 6, 6)
            if len(pts) == 2: painter.drawLine(pts[0], pts[1])

    def _draw_hud(self, painter):
        task = self.state.current_task
        text = [f'模式：{self.state.mode}']
        if task:
            text.append(f'任务：{task.road_name}')
            text.append(ImageCalibrationEngine.describe(task.meter_per_pixel))
            text.append(f'裂缝：{len(task.cracks)}  网裂区：{len(task.regions)}  疑似：{len([c for c in task.candidates if c.status=="待确认"])}')
        painter.setBrush(QColor(255, 255, 255, 232)); painter.setPen(QColor('#d9e1eb'))
        painter.drawRoundedRect(14, 14, 390, 96, 12, 12)
        painter.setPen(QColor('#24364b'))
        y = 36
        for line in text:
            painter.drawText(28, y, line); y += 21

    def _draw_scale_ruler(self, painter):
        task = self.state.current_task
        if self.pixmap.isNull():
            return
        img_x = self.offset.x()
        img_y = self.offset.y()
        img_w = self.pixmap.width() * self.scale
        img_h = self.pixmap.height() * self.scale
        ruler_h = 26
        ruler_w = 34
        top_y = max(0, img_y - ruler_h)
        left_x = max(0, img_x - ruler_w)

        painter.setPen(QPen(QColor('#c8d3e1'), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 238)))
        painter.drawRect(QRectF(img_x, top_y, img_w, ruler_h))
        painter.drawRect(QRectF(left_x, img_y, ruler_w, img_h))
        painter.fillRect(QRectF(left_x, top_y, ruler_w, ruler_h), QColor('#edf2f8'))

        # 类 PS 边缘游标卡尺：未标定显示像素，标定后显示实际距离。
        meter_per_pixel = task.meter_per_pixel if task else None
        if meter_per_pixel:
            major_px = max(1, 0.5 / meter_per_pixel)  # 每 0.5 米一个大刻度
            minor_px = major_px / 5
            unit_label = '米'
        else:
            major_px = 200
            minor_px = 50
            unit_label = '像素'

        painter.setFont(QFont('Microsoft YaHei', 8))
        painter.setPen(QPen(QColor('#31445b'), 1))

        def label_for(v_px):
            if meter_per_pixel:
                return f'{v_px * meter_per_pixel:.1f}'
            return f'{int(v_px)}'

        # 横向标尺
        max_px_x = self.pixmap.width()
        tick = 0.0
        while tick <= max_px_x:
            sx = img_x + tick * self.scale
            if sx >= img_x - 1 and sx <= img_x + img_w + 1:
                is_major = abs((tick / major_px) - round(tick / major_px)) < 0.01
                h = 14 if is_major else 7
                painter.drawLine(int(sx), int(top_y + ruler_h), int(sx), int(top_y + ruler_h - h))
                if is_major:
                    painter.drawText(int(sx + 3), int(top_y + 11), label_for(tick))
            tick += minor_px

        # 纵向标尺
        max_px_y = self.pixmap.height()
        tick = 0.0
        while tick <= max_px_y:
            sy = img_y + tick * self.scale
            if sy >= img_y - 1 and sy <= img_y + img_h + 1:
                is_major = abs((tick / major_px) - round(tick / major_px)) < 0.01
                w = 18 if is_major else 9
                painter.drawLine(int(left_x + ruler_w), int(sy), int(left_x + ruler_w - w), int(sy))
                if is_major:
                    painter.save()
                    painter.translate(int(left_x + 8), int(sy - 3))
                    painter.rotate(-90)
                    painter.drawText(0, 0, label_for(tick))
                    painter.restore()
            tick += minor_px

        painter.setPen(QColor('#31445b'))
        painter.drawText(int(left_x + 4), int(top_y + 18), unit_label)

        # 鼠标游标线，在边缘标尺上同步显示当前位置。
        if self.hover_world and self._inside_image(self.hover_world):
            hx = img_x + self.hover_world[0] * self.scale
            hy = img_y + self.hover_world[1] * self.scale
            painter.setPen(QPen(QColor('#1677ff'), 2))
            painter.drawLine(int(hx), int(top_y), int(hx), int(top_y + ruler_h))
            painter.drawLine(int(left_x), int(hy), int(left_x + ruler_w), int(hy))

    def wheelEvent(self, event):
        old_scale = self.scale; delta = event.angleDelta().y(); factor = 1.15 if delta > 0 else 0.87
        self.scale = max(0.08, min(6.0, self.scale * factor))
        pos = event.position(); wx = (pos.x() - self.offset.x()) / old_scale; wy = (pos.y() - self.offset.y()) / old_scale
        self.offset = QPointF(pos.x() - wx * self.scale, pos.y() - wy * self.scale)
        self.update()

    def mousePressEvent(self, event):
        if self.pixmap.isNull():
            return
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True; self.last_mouse = event.position(); return
        if event.button() == Qt.MouseButton.RightButton:
            self.finish_current_shape(); return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        world = self.screen_to_world(event.position()); mode = self.state.mode
        if mode == '浏览':
            if self.try_start_drag(world):
                return
            self.pick_crack_or_candidate(world)
        elif mode == '折线裂缝':
            self.add_polyline_point(world)
        elif mode == '比例标定':
            self.add_calibration_point(world)
        elif mode == '宽度卡尺':
            self.add_width_point(world)
        elif mode == '网裂圈选':
            self.state.region_pending_points.append(world)
            self.state.message.emit('已添加网裂区域顶点，右键闭合区域')
        self.update()

    def mouseMoveEvent(self, event):
        if self.panning:
            d = event.position() - self.last_mouse; self.offset += d; self.last_mouse = event.position(); self.update(); return
        world = self.screen_to_world(event.position()); self.hover_world = world
        if self.dragging_node is not None:
            crack, idx = self.dragging_node
            if not crack.locked and self._inside_image(world):
                crack.points[idx] = world
                CrackSeverityEvaluator.refresh_crack(crack, self.state.current_task.meter_per_pixel if self.state.current_task else None)
                self.canvas_changed.emit(); self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_node is not None:
            self.dragging_node = None
            self.refresh_all_measurements(); self.request_save.emit(); self.update()

    def mouseDoubleClickEvent(self, event):
        if self.state.mode == '折线裂缝':
            self.finish_polyline()

    def try_start_drag(self, world):
        task = self.state.current_task
        if not task:
            return False
        radius = 14 / max(self.scale, 0.1)

        # 先允许拖动当前选中裂缝的节点
        ordered = []
        selected = self.state.selected_crack()
        if selected:
            ordered.append(selected)
        ordered.extend([c for c in task.cracks if c is not selected])

        for crack in ordered:
            if crack.locked:
                continue
            idx = nearest_point_index(crack.points, world, radius=radius)
            if idx >= 0:
                self.state.select_crack(crack.crack_id)
                self.dragging_node = (crack, idx)
                self.state.message.emit('正在拖动裂缝节点，可用于修正自动识别结果')
                return True
        return False

    def add_polyline_point(self, world):
        task = self.state.current_task
        if not task:
            QMessageBox.warning(self, '没有任务', '请先在影像任务舱创建任务'); return
        if not self._inside_image(world):
            return
        x, y = self.state.snap_assistant.snap_qimage(self.qimage, *world)
        self.state.temporary_points.append((x, y))
        self.state.message.emit(self.state.snap_assistant.last_message if self.state.snap_assistant.enabled else '已添加裂缝节点，右键结束')

    def finish_polyline(self):
        task = self.state.current_task
        if not task or len(self.state.temporary_points) < 2:
            self.state.temporary_points.clear(); return
        crack = CrackObject(points=list(self.state.temporary_points))
        CrackSeverityEvaluator.refresh_crack(crack, task.meter_per_pixel)
        task.cracks.append(crack); task.status = '标注中'; task.touch(); self.state.temporary_points.clear(); self.state.select_crack(crack.crack_id)
        self.canvas_changed.emit(); self.request_save.emit(); self.state.message.emit(f'已生成可测量裂缝对象：{crack.crack_id}')

    def add_calibration_point(self, world):
        if not self._inside_image(world): return
        self.calibration_points.append(world)
        if len(self.calibration_points) == 2:
            real, ok = QInputDialog.getDouble(self, '比例尺标定', '请输入两点之间实际距离（米）：', 1.0, 0.001, 1000, 3)
            if ok:
                try:
                    mpp = ImageCalibrationEngine.calibrate_by_two_points(self.calibration_points[0], self.calibration_points[1], real)
                    task = self.state.current_task; task.meter_per_pixel = mpp; self.refresh_all_measurements(); self.state.message.emit(f'比例尺已锁定：1像素={mpp*1000:.3f}毫米')
                    self.canvas_changed.emit(); self.request_save.emit()
                except Exception as e:
                    QMessageBox.warning(self, '标定失败', str(e))
            self.calibration_points.clear()
            if self.state.mode == '比例标定':
                self.state.set_mode('浏览')

    def add_width_point(self, world):
        crack = self.state.selected_crack(); task = self.state.current_task
        if not task: return
        if not crack:
            QMessageBox.information(self, '先选择裂缝', '请先在画布或右侧卡片中选择一条裂缝'); return
        if crack.locked:
            QMessageBox.warning(self, '裂缝已锁定', '复核通过并锁定的裂缝不能继续添加宽度采样'); return
        if self.state.width_pending_point is None:
            self.state.width_pending_point = world; self.state.message.emit('已记录卡尺第一点，请点击裂缝另一侧')
        else:
            sample = CrackWidthGauge.make_sample(self.state.width_pending_point, world, task.meter_per_pixel)
            crack.width_samples.append(sample); self.state.width_pending_point = None; CrackSeverityEvaluator.refresh_crack(crack, task.meter_per_pixel)
            self.state.message.emit(f'宽度采样完成：{sample.width_mm:.2f}mm，{CrackWidthGauge.status_text(sample.width_mm)}')
            self.canvas_changed.emit(); self.request_save.emit()

    def finish_region(self):
        task = self.state.current_task; pts = list(self.state.region_pending_points)
        if not task or len(pts) < 3:
            self.state.region_pending_points.clear(); return
        region = CrackRegion(polygon_points=pts)
        region.area_m2 = CrackRegionAnalyzer.area(pts, task.meter_per_pixel)
        total_len = sum(polyline_length_real(c.points, task.meter_per_pixel) for c in task.cracks)
        if not task.meter_per_pixel: total_len = total_len / 180
        region.density = CrackRegionAnalyzer.density(total_len, region.area_m2); region.severity = CrackRegionAnalyzer.severity(region.area_m2, region.density)
        task.regions.append(region); task.status = '标注中'; self.state.region_pending_points.clear(); self.state.message.emit(f'网裂区域已生成：面积 {region.area_m2:.2f}㎡，等级 {region.severity}')
        self.canvas_changed.emit(); self.request_save.emit()

    def finish_current_shape(self):
        if self.state.mode == '折线裂缝': self.finish_polyline()
        elif self.state.mode == '网裂圈选': self.finish_region()
        else: self.pick_crack_or_candidate(self.screen_to_world(self.mapFromGlobal(self.cursor().pos())))
        self.update()

    def pick_crack_or_candidate(self, world):
        task = self.state.current_task
        if not task: return
        for candidate in task.candidates:
            if candidate.status != '待确认': continue
            if any(distance(world, p) < 15 / max(self.scale, 0.1) for p in candidate.points):
                reply = QMessageBox.question(self, '疑似裂缝', '是否将该疑似暗线转为正式裂缝？', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    crack = CrackObject(points=list(candidate.points), source='漏标扫描转正')
                    CrackSeverityEvaluator.refresh_crack(crack, task.meter_per_pixel)
                    task.cracks.append(crack); candidate.status = '已转正'; self.state.select_crack(crack.crack_id); self.state.message.emit('疑似裂缝已转为正式裂缝')
                    self.canvas_changed.emit(); self.request_save.emit()
                else:
                    candidate.status = '已忽略'; self.state.message.emit('疑似裂缝已忽略'); self.canvas_changed.emit(); self.request_save.emit()
                return
        best_id = None
        best_d = 24 / max(self.scale, 0.1)
        for crack in task.cracks:
            if len(crack.points) < 2:
                continue
            for a, b in zip(crack.points[:-1], crack.points[1:]):
                d = self._point_segment_distance(world, a, b)
                if d < best_d:
                    best_id = crack.crack_id
                    best_d = d
        self.state.select_crack(best_id)

    def undo_last_point(self):
        if self.state.mode == '折线裂缝' and self.state.temporary_points:
            self.state.temporary_points.pop()
        elif self.state.mode == '网裂圈选' and self.state.region_pending_points:
            self.state.region_pending_points.pop()
        self.update()

    def smooth_selected_crack(self):
        crack = self.state.selected_crack()
        if not crack: return False
        if crack.locked:
            QMessageBox.warning(self, '已锁定', '该裂缝已锁定，不能平滑。'); return False
        crack.points = smooth_polyline(crack.points, 0.55, 2); CrackSeverityEvaluator.refresh_crack(crack, self.state.current_task.meter_per_pixel); self.canvas_changed.emit(); self.request_save.emit(); self.update(); return True

    def delete_selected_any_annotation(self):
        task = self.state.current_task
        crack = self.state.selected_crack()
        if not task or not crack:
            return False, '请先选择一条标注线'
        if crack.locked:
            return False, '该裂缝已锁定，请先在复核纠偏舱解除锁定'
        task.cracks = [c for c in task.cracks if c.crack_id != crack.crack_id]
        task.touch()
        self.state.select_crack(None)
        self.canvas_changed.emit()
        self.request_save.emit()
        self.update()
        return True, '已删除选中标注线'

    def delete_auto_detected_annotations(self):
        task = self.state.current_task
        if not task:
            return 0
        before = len(task.cracks)
        task.cracks = [c for c in task.cracks if c.source != '自动识别']
        removed = before - len(task.cracks)
        if removed:
            task.touch()
            self.state.select_crack(None)
            self.canvas_changed.emit()
            self.request_save.emit()
            self.update()
        return removed

    def clear_candidates(self):
        task = self.state.current_task
        if not task:
            return 0
        count = len(task.candidates)
        task.candidates.clear()
        task.touch()
        self.canvas_changed.emit()
        self.request_save.emit()
        self.update()
        return count

    def delete_selected_crack(self):
        task = self.state.current_task; crack = self.state.selected_crack()
        if not task or not crack: return False
        if crack.locked:
            QMessageBox.warning(self, '已锁定', '已锁定裂缝不能删除。'); return False
        task.cracks = [c for c in task.cracks if c.crack_id != crack.crack_id]; self.state.select_crack(None); self.canvas_changed.emit(); self.request_save.emit(); self.update(); return True

    def refresh_all_measurements(self):
        task = self.state.current_task
        if not task: return
        for crack in task.cracks:
            for sample in crack.width_samples:
                sample.width_mm = CrackWidthGauge.make_sample(sample.p1, sample.p2, task.meter_per_pixel).width_mm
            CrackSeverityEvaluator.refresh_crack(crack, task.meter_per_pixel)
        for region in task.regions:
            region.area_m2 = CrackRegionAnalyzer.area(region.polygon_points, task.meter_per_pixel)
            total_len = sum(polyline_length_real(c.points, task.meter_per_pixel) for c in task.cracks)
            if not task.meter_per_pixel: total_len = total_len / 180
            region.density = CrackRegionAnalyzer.density(total_len, region.area_m2); region.severity = CrackRegionAnalyzer.severity(region.area_m2, region.density)
        task.touch(); self.update()

    def _point_segment_distance(self, p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b
        vx, vy = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        denom = vx * vx + vy * vy
        if denom <= 1e-9:
            return distance(p, a)
        t = max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
        q = (ax + t * vx, ay + t * vy)
        return distance(p, q)

    def _inside_image(self, p):
        if self.pixmap.isNull(): return False
        return 0 <= p[0] <= self.pixmap.width() and 0 <= p[1] <= self.pixmap.height()
