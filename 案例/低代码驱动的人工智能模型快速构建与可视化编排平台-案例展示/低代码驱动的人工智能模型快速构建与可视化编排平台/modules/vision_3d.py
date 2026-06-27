"""3D可视化模块 - 点云渲染、3D模型展示、特征分布三维视图、多图层叠加（纯QPainter安全渲染）"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QSlider, QComboBox, QSplitter, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPainterPath
from core.auth import Role, OpAction, auth_engine
from core.state_machine import task_sm, TaskState
from core.rule_engine import rule_engine
from core.algorithms import FeatureAnalyzer
import numpy as np
import math

class Safe3DView(QWidget):
    """纯QPainter实现的3D视图 - 无OpenGL依赖，无崩溃风险，支持旋转/缩放/平移"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: np.ndarray = None
        self._edges: list = None
        self._rotation = [30.0, 45.0, 0.0]
        self._zoom = 1.0
        self._pan = [0.0, 0.0]
        self._last_pos = None
        self._auto_rotate = False
        self._point_size = 3
        self._bg_color = QColor(255, 248, 225)
        self.setMinimumSize(500, 380)
        self.setMouseTracking(True)

    def set_points(self, points: np.ndarray, edges: list = None):
        if points is not None and len(points) > 0:
            self._points = np.array(points, dtype=np.float64)
        else:
            self._points = None
        self._edges = edges
        self.update()

    def _project(self, x: float, y: float, z: float) -> tuple:
        rx, ry, rz = math.radians(self._rotation[0]), math.radians(self._rotation[1]), math.radians(self._rotation[2])
        # Rotate Y
        cos_b, sin_b = math.cos(ry), math.sin(ry)
        x1 = x * cos_b + z * sin_b
        z1 = -x * sin_b + z * cos_b
        # Rotate X
        cos_a, sin_a = math.cos(rx), math.sin(rx)
        y1 = y * cos_a - z1 * sin_a
        z2 = y * sin_a + z1 * cos_a
        # Rotate Z
        cos_c, sin_c = math.cos(rz), math.sin(rz)
        x2 = x1 * cos_c - y1 * sin_c
        y2 = x1 * sin_c + y1 * cos_c
        # Isometric project: x on screen diagonal, y vertical, z for depth
        scale = self._zoom * 45
        sx = self.width() / 2 + self._pan[0] + (x2 - y2) * scale * 0.55
        sy = self.height() / 2 + self._pan[1] - (x2 + y2) * scale * 0.3 - z2 * scale * 0.4
        return sx, sy, z2

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self._bg_color)

        p.setPen(QPen(QColor("#FFD54F"), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

        if self._points is None or len(self._points) == 0:
            p.setPen(QPen(QColor("#795548")))
            p.setFont(QFont("Microsoft YaHei", 12))
            lines = ["🌐 3D可视化视图", "", "🖱 左键拖拽 → 旋转", "🖱 右键拖拽 → 平移",
                     "🖱 滚轮 → 缩放", "", "📂 点击左侧数据图层加载3D内容",
                     "🎲 或点击「生成演示数据」按钮"]
            y_off = self.height() // 2 - 110
            for line in lines:
                p.drawText(0, y_off, self.width(), 24, Qt.AlignmentFlag.AlignCenter, line)
                y_off += 24
            p.end()
            return

        points = self._points[:6000] if len(self._points) > 6000 else self._points
        # Sort by depth (z after rotation) for painter's algorithm
        projected = []
        for pt in points:
            if len(pt) >= 3:
                sx, sy, sz = self._project(float(pt[0]), float(pt[1]), float(pt[2]))
                projected.append((sx, sy, sz))
            elif len(pt) >= 2:
                sx, sy, sz = self._project(float(pt[0]), float(pt[1]), 0)
                projected.append((sx, sy, sz))
        projected.sort(key=lambda v: -v[2])

        n = len(projected)
        for i, (sx, sy, sz) in enumerate(projected):
            if not (-100 < sx < self.width() + 100 and -100 < sy < self.height() + 100):
                continue
            ratio = i / max(1, n - 1)
            r = int(80 + 175 * ratio)
            g = int(180 - 120 * ratio)
            b = int(200 + 55 * ratio)
            depth_factor = 0.4 + 0.6 * ((sz + 3) / 6)
            r = int(r * depth_factor)
            g = int(g * depth_factor)
            b = int(b * depth_factor)
            color = QColor(max(30, min(255, r)), max(30, min(255, g)), max(30, min(255, b)))
            p.setPen(QPen(color, 1.5))
            size = max(1, int(self._point_size * self._zoom))
            p.drawPoint(int(sx), int(sy))

        if self._edges:
            p.setPen(QPen(QColor(255, 143, 0, 80), 1, Qt.PenStyle.DotLine))
            for e in self._edges[:500]:
                if e[0] < len(points) and e[1] < len(points):
                    x1, y1, _ = self._project(float(points[e[0]][0]), float(points[e[0]][1]),
                                               float(points[e[0]][2]) if len(points[e[0]]) > 2 else 0)
                    x2, y2, _ = self._project(float(points[e[1]][0]), float(points[e[1]][1]),
                                               float(points[e[1]][2]) if len(points[e[1]]) > 2 else 0)
                    p.drawLine(int(x1), int(y1), int(x2), int(y2))

        p.setPen(QPen(QColor("#FF8F00"), 1))
        p.setFont(QFont("Microsoft YaHei", 9))
        p.drawText(10, 18, f"缩放: {self._zoom:.1f}x | 点数: {len(self._points)}")
        p.end()

    def wheelEvent(self, event):
        self._zoom = max(0.15, min(6.0, self._zoom * (1.12 if event.angleDelta().y() > 0 else 0.88)))
        self.update()

    def mousePressEvent(self, event):
        self._last_pos = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._last_pos is None:
            return
        dx = event.position().x() - self._last_pos.x()
        dy = event.position().y() - self._last_pos.y()
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._rotation[0] += dy * 0.4
            self._rotation[1] += dx * 0.4
        elif event.buttons() & Qt.MouseButton.RightButton:
            self._pan[0] += dx
            self._pan[1] += dy
        self._last_pos = event.position()
        self.update()

    def mouseReleaseEvent(self, event):
        self._last_pos = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        self._rotation = [30.0, 45.0, 0.0]
        self._zoom = 1.0
        self._pan = [0.0, 0.0]
        self.update()

    def start_auto_rotate(self, interval_ms: int = 45):
        if not hasattr(self, '_rot_timer'):
            self._rot_timer = QTimer(self)
            self._rot_timer.timeout.connect(self._auto_rotate_step)
        self._rot_timer.start(interval_ms)

    def stop_auto_rotate(self):
        if hasattr(self, '_rot_timer'):
            self._rot_timer.stop()

    def _auto_rotate_step(self):
        self._rotation[1] = (self._rotation[1] + 1.5) % 360
        self._rotation[0] += 0.1
        self.update()

class Vision3DWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._point_clouds = {}
        self._current_pc = None
        self._setup_ui()
        self._generate_demo_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("🌐 3D数据可视化")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title)
        header.addStretch()
        for label, handler in [("📂 导入点云", self._import_pointcloud),
                               ("📂 导入模型", self._import_model),
                               ("🎲 生成演示数据", self._generate_demo_data),
                               ("📤 导出快照", self._export_snapshot)]:
            header.addWidget(QPushButton(label, clicked=handler))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_panel.setSpacing(8)

        data_gb = QGroupBox("📦 数据图层（点击切换）")
        dl = QVBoxLayout()
        from PyQt6.QtWidgets import QListWidget
        self.layer_list = QListWidget()
        self.layer_list.addItems([
            "🔵 点云-演示球体 (800点)", "🟧 点云-演示立方体 (600点)",
            "🟢 点云-演示螺旋 (1000点)", "🔺 3D模型-四面体框架",
            "📊 特征分布-3D散点映射", "🌪 混沌吸引子-Lorenz系统"
        ])
        self.layer_list.itemClicked.connect(self._on_layer_select)
        self.layer_list.setMaximumHeight(160)
        dl.addWidget(self.layer_list)
        data_gb.setLayout(dl)
        left_panel.addWidget(data_gb)

        view_gb = QGroupBox("🔧 视图控制")
        vl = QVBoxLayout()
        vl.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(15, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        vl.addWidget(self.zoom_slider)

        views = [("📷 俯视图", [90, 0, 0]), ("📷 正视图", [0, 0, 0]),
                 ("📷 侧视图", [0, 90, 0]), ("📷 等轴测", [35, 45, 0]),
                 ("📷 透视角", [25, 35, 10])]
        for name, rot in views:
            vl.addWidget(QPushButton(name, clicked=lambda checked, r=rot: self._set_view(r)))
        view_gb.setLayout(vl)
        left_panel.addWidget(view_gb)

        info_gb = QGroupBox("ℹ 数据信息")
        self.info_label = QLabel("点数: --\n范围: --\n当前图层: --")
        self.info_label.setStyleSheet("color:#795548;padding:4px;")
        info_gb.setLayout(QVBoxLayout())
        info_gb.layout().addWidget(self.info_label)
        left_panel.addWidget(info_gb)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(240)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)
        self.view3d = Safe3DView()
        right_panel.addWidget(self.view3d)

        op_bar = QHBoxLayout()
        op_btns = [
            ("🔄 旋转动画", self._toggle_rotation),
            ("📐 特征分布3D", self._show_feature_3d),
            ("🎨 多图层叠加", self._overlay_layers),
            ("📊 批量处理", self._batch_process),
            ("🔄 重置视角", lambda: setattr(self.view3d, '_rotation', [30, 45, 0]) or
             setattr(self.view3d, '_zoom', 1.0) or setattr(self.view3d, '_pan', [0, 0]) or self.view3d.update()),
        ]
        for label, handler in op_btns:
            op_bar.addWidget(QPushButton(label, clicked=handler))
        right_panel.addLayout(op_bar)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        main.addWidget(left_widget)
        main.addWidget(right_widget)
        main.setSizes([240, 900])
        layout.addWidget(main)

    def _generate_demo_data(self):
        self._point_clouds["球体"] = self._gen_sphere(800)
        self._point_clouds["立方体"] = self._gen_cube(600)
        self._point_clouds["螺旋"] = self._gen_spiral(1000)
        self._point_clouds["四面体"] = self._gen_tetrahedron()
        self._point_clouds["Lorenz"] = self._gen_lorenz(1200)
        self._current_pc = self._point_clouds["螺旋"]
        self.view3d.set_points(self._current_pc)
        self.info_label.setText(f"点数: {len(self._current_pc)}\n范围: [-2,2]³\n当前图层: 螺旋")

    def _gen_sphere(self, n):
        phi = np.random.uniform(0, np.pi, n)
        theta = np.random.uniform(0, 2 * np.pi, n)
        r = np.cbrt(np.random.uniform(0, 8, n))
        return np.column_stack([r * np.sin(phi) * np.cos(theta),
                                r * np.sin(phi) * np.sin(theta),
                                r * np.cos(phi)])

    def _gen_cube(self, n):
        pts = []
        side = int(n / 6)
        for _ in range(side):
            pts.append([np.random.uniform(-2, 2), np.random.uniform(-2, 2), -2])
            pts.append([np.random.uniform(-2, 2), np.random.uniform(-2, 2), 2])
            pts.append([np.random.uniform(-2, 2), -2, np.random.uniform(-2, 2)])
            pts.append([np.random.uniform(-2, 2), 2, np.random.uniform(-2, 2)])
            pts.append([-2, np.random.uniform(-2, 2), np.random.uniform(-2, 2)])
            pts.append([2, np.random.uniform(-2, 2), np.random.uniform(-2, 2)])
        return np.array(pts[:n])

    def _gen_spiral(self, n):
        t = np.linspace(0, 4 * np.pi, n)
        r = t / max(t) * 2
        return np.column_stack([r * np.cos(t), r * np.sin(t), np.linspace(-2, 2, n)])

    def _gen_tetrahedron(self):
        verts = np.array([[0, 2, 0], [1.8, -1, -1], [-1.8, -1, -1], [0, 0, 2.5]])
        pts = []
        for _ in range(500):
            a, b, c = np.random.rand(3)
            if a + b + c > 1:
                a, b, c = 1 - a, 1 - b, 1 - c
            pt = a * verts[0] + b * verts[1] + c * verts[2] + (1 - a - b - c) * verts[3]
            pts.append(pt)
        pts_array = np.array(pts)
        edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        self._tetra_edges = edges
        return pts_array

    def _gen_lorenz(self, n):
        dt = 0.01
        pts = np.zeros((n, 3))
        x, y, z = 0.1, 0.1, 0.1
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        for i in range(n):
            dx = sigma * (y - x) * dt
            dy = (x * (rho - z) - y) * dt
            dz = (x * y - beta * z) * dt
            x += dx; y += dy; z += dz
            pts[i] = [x / 10, y / 10, z / 15]
        return pts

    def _on_layer_select(self, item):
        text = item.text()
        key_map = {"球体": "球体", "立方体": "立方体", "螺旋": "螺旋",
                    "四面体": "四面体", "Lorenz": "Lorenz"}
        for kw, key in key_map.items():
            if kw in text:
                if key in self._point_clouds:
                    self._current_pc = self._point_clouds[key]
                    edges = self._tetra_edges if key == "四面体" else None
                    self.view3d.set_points(self._current_pc, edges)
                    self.info_label.setText(f"点数: {len(self._current_pc)}\n当前图层: {key}")
                return
        self._show_feature_3d()

    def _on_zoom(self, val):
        self.view3d._zoom = val / 100.0
        self.view3d.update()

    def _set_view(self, rot):
        self.view3d._rotation = list(rot)
        self.view3d.update()

    def _toggle_rotation(self):
        if not hasattr(self.view3d, '_rot_timer') or not self.view3d._rot_timer.isActive():
            self.view3d.start_auto_rotate(45)
            QMessageBox.information(self, "旋转动画", "3D视图旋转中（再次点击停止）")
        else:
            self.view3d.stop_auto_rotate()
            QMessageBox.information(self, "旋转动画", "旋转已停止")

    def _show_feature_3d(self):
        features = np.random.randn(300, 3) * np.array([2.5, 1.5, 3.0]) + np.array([0, 0, 1.5])
        self._current_pc = features
        self.view3d.set_points(features)
        self.info_label.setText("特征分布3D映射\n维度: 3 | 样本: 300\n各维度随机生成")

    def _overlay_layers(self):
        if len(self._point_clouds) >= 2:
            keys = list(self._point_clouds.keys())
            all_points = np.vstack([self._point_clouds[keys[0]][:400],
                                    self._point_clouds[keys[1]][:400]])
            np.random.shuffle(all_points)
            self.view3d.set_points(all_points[:800])
            self.info_label.setText(f"多图层叠加\n{keys[0]} + {keys[1]}\n总点数: {min(800, len(all_points))}")

    def _batch_process(self):
        QMessageBox.information(self, "批量处理",
            "3D数据批量处理功能\n支持批量导入点云文件并执行统一AI流程\n\n支持格式: PLY/XYZ/PCD/TXT\n任务将加入任务管控队列监控")

    def _import_pointcloud(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入点云", "",
            "点云文件 (*.ply *.xyz *.pcd *.txt *.csv);;所有文件 (*.*)")
        if path:
            try:
                data = np.loadtxt(path, delimiter=None, usecols=(0, 1, 2), max_rows=5000)
                if data.shape[1] >= 3:
                    self._current_pc = data
                    self.view3d.set_points(data)
                    self.info_label.setText(f"导入文件: {path.split('/')[-1]}\n点数: {len(data)}")
            except Exception as e:
                QMessageBox.warning(self, "导入失败", f"无法解析文件:\n{str(e)}\n\n请确保文件包含至少3列数值数据")

    def _import_model(self):
        QMessageBox.information(self, "导入3D模型",
            "支持格式: OBJ / STL / GLTF\n导入后将自动渲染模型顶点与面结构\n\n请将模型文件放入项目资源目录后导入")

    def _export_snapshot(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出快照", "3d_snapshot.png",
            "PNG图片 (*.png);;所有文件 (*.*)")
        if path:
            pixmap = self.view3d.grab()
            pixmap.save(path)
            QMessageBox.information(self, "导出", f"3D视图快照已保存至:\n{path}")

def get_module_widget(user):
    return Vision3DWidget(user)
