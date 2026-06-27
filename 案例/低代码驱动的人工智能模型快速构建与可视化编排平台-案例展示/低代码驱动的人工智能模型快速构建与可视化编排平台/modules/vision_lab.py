"""视觉实验室(OpenCV) - 图像预处理/滤波/边缘/分割/阈值/形态学 + 视觉推理"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QSlider, QComboBox, QFileDialog, QScrollArea, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from core.auth import Role, OpAction, auth_engine
from core.rule_engine import rule_engine, TriggerType, Condition, CompareOp, RuleAction
from core.state_machine import task_sm, TaskState
import numpy as np
import cv2

class ImageViewer(QWidget):
    """可滚轮缩放的图像查看器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None; self._scale = 1.0; self._offset_x = 0; self._offset_y = 0
        self.setMinimumSize(400, 300); self.setMouseTracking(True)

    def set_image(self, img_array):
        if img_array is None: return
        if len(img_array.shape) == 2:
            h, w = img_array.shape
            qimg = QImage(img_array.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            h, w, ch = img_array.shape
            qimg = QImage(img_array.data, w, h, w * ch, QImage.Format.Format_BGR888)
        self._pixmap = QPixmap.fromImage(qimg); self.update()

    def wheelEvent(self, event):
        if self._pixmap:
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self._scale = max(0.1, min(5.0, self._scale * factor))
            self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(255, 248, 225))
        if self._pixmap:
            scaled = self._pixmap.scaled(self._pixmap.size() * self._scale,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2 + int(self._offset_x)
            y = (self.height() - scaled.height()) // 2 + int(self._offset_y)
            p.drawPixmap(x, y, scaled)
            p.setPen(QPen(QColor("#FF8F00"), 1))
            p.drawText(10, 20, f"缩放: {self._scale:.1f}x")
        else:
            p.setPen(QPen(QColor("#795548")))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "请加载图像或生成演示图像")

class VisionLabWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._original_img = None
        self._processed_img = None
        self._setup_ui()
        self._init_demo_image()
        self._init_rules()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("👁 视觉实验室 (OpenCV)")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        header.addWidget(QPushButton("📂 加载图片", clicked=self._load_image))
        header.addWidget(QPushButton("🎥 加载视频", clicked=self._load_video))
        header.addWidget(QPushButton("📷 摄像头", clicked=self._capture_camera))
        header.addWidget(QPushButton("🔄 重置", clicked=self._reset_image))
        header.addWidget(QPushButton("💾 导出结果", clicked=self._export_result))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        ops_gb = QGroupBox("🛠 图像处理操作(可自定义参数)")
        og = QGridLayout()
        operations = [
            ("灰度化", "gray"), ("高斯模糊", "blur"), ("边缘检测(Canny)", "canny"),
            ("阈值分割", "threshold"), ("形态学膨胀", "dilate"), ("形态学腐蚀", "erode"),
            ("Sobel梯度", "sobel"), ("直方图均衡", "equalize"),
        ]
        self._op_btns = {}
        self._op_sliders = {}
        for i, (name, key) in enumerate(operations):
            btn = QPushButton(name); btn.setCheckable(True)
            self._op_btns[key] = btn; og.addWidget(btn, i, 0)
            slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(1, 200); slider.setValue(100)
            self._op_sliders[key] = slider; og.addWidget(slider, i, 1)
        ops_gb.setLayout(og)
        left_panel.addWidget(ops_gb)

        apply_btn = QPushButton("⚡ 应用处理链"); apply_btn.setObjectName("primary")
        apply_btn.clicked.connect(self._apply_processing_chain)
        left_panel.addWidget(apply_btn)

        inference_gb = QGroupBox("🤖 AI推理(模拟)")
        il = QVBoxLayout()
        il.addWidget(QPushButton("🔍 目标检测推理", clicked=self._run_detection))
        il.addWidget(QPushButton("🏷 图像分类推理", clicked=self._run_classification))
        il.addWidget(QPushButton("✂ 语义分割推理", clicked=self._run_segmentation))
        inference_gb.setLayout(il)
        left_panel.addWidget(inference_gb)

        stats_gb = QGroupBox("📊 图像统计")
        self.stats_label = QLabel("分辨率: --\n通道数: --\n像素范围: --")
        self.stats_label.setStyleSheet("color:#795548;")
        stats_gb.setLayout(QVBoxLayout()); stats_gb.layout().addWidget(self.stats_label)
        left_panel.addWidget(stats_gb)

        left_widget = QWidget(); left_widget.setLayout(left_panel); left_widget.setMaximumWidth(240)

        right_panel = QVBoxLayout()
        img_row = QHBoxLayout()
        self.original_view = ImageViewer()
        self.processed_view = ImageViewer()
        img_row.addWidget(QLabel("原始图像", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="color:#E65100;"))
        img_row.addWidget(QLabel("处理后图像", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="color:#2E7D32;"))
        right_panel.addLayout(img_row)

        viewer_row = QHBoxLayout()
        viewer_row.addWidget(self.original_view); viewer_row.addWidget(self.processed_view)
        right_panel.addLayout(viewer_row)

        right_widget = QWidget(); right_widget.setLayout(right_panel)
        main.addWidget(left_widget); main.addWidget(right_widget)
        main.setSizes([240, 900])
        layout.addWidget(main)

    def _init_demo_image(self):
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        img[:] = (30, 30, 50)
        # 绘制模拟图像内容
        cv2.rectangle(img, (50, 50), (200, 200), (0, 100, 200), -1)
        cv2.rectangle(img, (250, 100), (400, 250), (0, 150, 100), -1)
        cv2.circle(img, (450, 150), 60, (200, 100, 0), -1)
        cv2.circle(img, (150, 300), 40, (150, 50, 150), -1)
        cv2.putText(img, "低代码AI平台 Demo", (200, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 255), 2)
        cv2.line(img, (0, 200), (600, 200), (100, 100, 100), 2)
        cv2.line(img, (300, 0), (300, 400), (100, 100, 100), 2)
        self._original_img = img
        self.original_view.set_image(img)
        self._update_stats(img)

    def _apply_processing_chain(self):
        if self._original_img is None:
            QMessageBox.warning(self, "提示", "请先加载图像或使用演示图像"); return
        img = self._original_img.copy()
        for key, btn in self._op_btns.items():
            if btn.isChecked():
                param = self._op_sliders[key].value() / 100.0
                img = self._process_single(img, key, param)
        self._processed_img = img
        self.processed_view.set_image(img)
        self._update_stats(img)

    def _process_single(self, img, op_key: str, param: float):
        try:
            if op_key == "gray":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            if op_key == "blur":
                ksize = max(3, int(param * 20))
                if ksize % 2 == 0: ksize += 1
                return cv2.GaussianBlur(img, (ksize, ksize), 0)
            if op_key == "canny":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                low = int(50 * param); high = int(150 * param)
                edges = cv2.Canny(gray, low, high)
                return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            if op_key == "threshold":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                thresh_val = int(127 * param)
                _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
                return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            if op_key == "dilate":
                kernel = np.ones((3, 3), np.uint8)
                return cv2.dilate(img, kernel, iterations=max(1, int(param * 3)))
            if op_key == "erode":
                kernel = np.ones((3, 3), np.uint8)
                return cv2.erode(img, kernel, iterations=max(1, int(param * 3)))
            if op_key == "sobel":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                mag = cv2.magnitude(sx, sy)
                mag = np.uint8(np.clip(mag * param, 0, 255))
                return cv2.cvtColor(mag, cv2.COLOR_GRAY2BGR)
            if op_key == "equalize":
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                eq = cv2.equalizeHist(gray)
                return cv2.cvtColor(eq, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            QMessageBox.warning(self, "处理异常", str(e))
        return img

    def _run_detection(self):
        if self._original_img is None: return
        img = self._original_img.copy()
        cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), 3)
        cv2.putText(img, "Object:0.92", (55, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.rectangle(img, (250, 100), (400, 250), (255, 0, 0), 3)
        cv2.putText(img, "Object:0.87", (255, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        self.processed_view.set_image(img)
        self._processed_img = img

    def _run_classification(self):
        if self._original_img is None: return
        img = self._original_img.copy()
        cv2.putText(img, "Class: vehicle (93.2%)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(img, "Class: building (5.1%)", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 200, 255), 2)
        self.processed_view.set_image(img); self._processed_img = img

    def _run_segmentation(self):
        if self._original_img is None: return
        img = self._original_img.copy()
        mask = np.zeros(img.shape[:2], np.uint8)
        cv2.circle(mask, (150, 150), 90, 128, -1)
        cv2.circle(mask, (450, 150), 80, 200, -1)
        overlay = img.copy()
        overlay[mask == 128] = (0, 255, 0); overlay[mask == 200] = (255, 0, 0)
        img = cv2.addWeighted(img, 0.5, overlay, 0.5, 0)
        self.processed_view.set_image(img); self._processed_img = img

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "",
            "图像文件 (*.png *.jpg *.bmp *.tiff *.webp);;所有文件 (*.*)")
        if path:
            img = cv2.imread(path)
            if img is not None:
                self._original_img = img; self.original_view.set_image(img); self._update_stats(img)

    def _load_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)")
        if path:
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read(); cap.release()
            if ret:
                self._original_img = frame; self.original_view.set_image(frame)
                self._update_stats(frame)
                QMessageBox.information(self, "视频加载", f"已加载视频首帧\n可使用视觉推理进行分析")

    def _capture_camera(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read(); cap.release()
        if ret:
            self._original_img = frame; self.original_view.set_image(frame)
            self._update_stats(frame)

    def _reset_image(self):
        self._init_demo_image(); self._processed_img = None
        self.processed_view._pixmap = None; self.processed_view.update()

    def _export_result(self):
        if self._processed_img is not None:
            path, _ = QFileDialog.getSaveFileName(self, "导出结果", "result.png", "PNG (*.png);;JPG (*.jpg)")
            if path: cv2.imwrite(path, self._processed_img)
        else:
            QMessageBox.warning(self, "提示", "请先处理图像")

    def _update_stats(self, img):
        h, w = img.shape[:2]
        ch = 1 if len(img.shape) == 2 else img.shape[2]
        self.stats_label.setText(f"分辨率: {w}×{h}\n通道数: {ch}\n像素范围: [{img.min()}, {img.max()}]")

    def _init_rules(self):
        rule_engine.create_rule("图像尺寸检查", TriggerType.DATA,
            [Condition(field="width", op=CompareOp.GT, value=32),
             Condition(field="height", op=CompareOp.GT, value=32)],
            [RuleAction(action_type="alert", params={"msg": "图像尺寸合法"})], priority=5, group="视觉处理")

def get_module_widget(user):
    return VisionLabWidget(user)
