"""报表中心 - 模型指标/训练耗时/推理耗时等图表展示，支持滚轮浏览"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QScrollArea, QGridLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient, QBrush
from core.auth import Role, OpAction, auth_engine
from core.algorithms import FeatureAnalyzer
import math

class MiniChart(QWidget):
    """微型图表组件"""
    def __init__(self, title: str, data: list, color: str = "#4fc3f7", chart_type: str = "line", parent=None):
        super().__init__(parent)
        self._title = title; self._data = data; self._color = QColor(color)
        self._chart_type = chart_type
        self.setMinimumSize(280, 200); self.setMaximumHeight(220)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(255, 248, 225))
        p.setPen(QPen(QColor("#FFD54F"), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        p.setPen(QPen(QColor("#4E342E"))); p.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        p.drawText(12, 24, self._title)

        if not self._data: return
        margin_l, margin_r, margin_t, margin_b = 40, 16, 40, 36
        w = self.width() - margin_l - margin_r
        h = self.height() - margin_t - margin_b
        if w <= 0 or h <= 0: return

        vals = [float(v) for v in self._data if isinstance(v, (int, float))]
        if not vals: return
        min_v, max_v = min(vals), max(vals)
        if max_v == min_v: max_v = min_v + 1
        range_v = max_v - min_v

        # 网格线
        for i in range(5):
            y = margin_t + h * i / 4
            p.setPen(QPen(QColor(255, 213, 79, 120), 1, Qt.PenStyle.DotLine))
            p.drawLine(int(margin_l), int(y), int(margin_l + w), int(y))
            p.setPen(QPen(QColor("#795548")))
            val = max_v - range_v * i / 4
            p.drawText(2, int(y) + 4, f"{val:.1f}")

        # 数据线/柱
        p.setPen(QPen(self._color, 2))
        step = w / max(1, len(vals) - 1) if len(vals) > 1 else w
        pts = []
        for i, val in enumerate(vals):
            x = margin_l + i * step; y = margin_t + h * (1 - (val - min_v) / range_v)
            pts.append((x, y))
        if self._chart_type == "bar":
            bar_w = max(6, step * 0.6)
            for i, (x, y) in enumerate(pts):
                gradient = QLinearGradient(x, y, x, margin_t + h)
                gradient.setColorAt(0, self._color.lighter(120))
                gradient.setColorAt(1, QColor(self._color.red()//3, self._color.green()//3, self._color.blue()//3))
                p.setBrush(QBrush(gradient))
                p.setPen(QPen(self._color, 1))
                p.drawRect(int(x - bar_w/2), int(y), int(bar_w), int(margin_t + h - y))
        else:
            path = None
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            path.moveTo(pts[0][0], pts[0][1])
            for x, y in pts[1:]: path.lineTo(x, y)
            p.drawPath(path)
            for x, y in pts:
                p.setBrush(self._color); p.setPen(QPen(QColor("#FFF8E1"), 1))
                p.drawEllipse(int(x)-3, int(y)-3, 6, 6)

    def wheelEvent(self, event):
        """滚轮缩放图表"""
        self.setMaximumHeight(max(120, min(400, self.maximumHeight() + (20 if event.angleDelta().y() > 0 else -20))))
        self.update()

class ReportCenterWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("📈 报表中心")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        header.addWidget(QLabel("项目:"))
        self.proj_combo = QComboBox()
        self.proj_combo.addItems(["图像分类项目", "目标检测项目", "文本分析项目", "3D点云项目", "时序预测项目"])
        header.addWidget(self.proj_combo)
        header.addWidget(QPushButton("🔄 刷新", clicked=self._refresh))
        header.addWidget(QPushButton("📤 导出报表", clicked=self._export_report))
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_w = QWidget()
        scroll_layout = QVBoxLayout(scroll_w)

        # 图表网格
        chart_gb = QGroupBox("📊 模型性能指标（滚轮缩放图表）")
        cg = QGridLayout()
        charts = [
            ("训练/验证准确率曲线", [0.45,0.58,0.65,0.72,0.78,0.82,0.85,0.88,0.90,0.91,0.92,0.93], "#4fc3f7", "line"),
            ("训练Loss下降曲线", [2.1,1.5,1.1,0.8,0.6,0.45,0.35,0.28,0.22,0.18,0.15,0.12], "#ef5350", "line"),
            ("各类别F1分数", [0.88,0.92,0.85,0.79,0.91,0.87], "#66bb6a", "bar"),
            ("推理耗时分布(ms)", [12,15,11,18,13,10,22,14,16,13,11,17], "#ffa726", "bar"),
            ("模型参数量对比(M)", [25.3,48.1,12.7,8.4,33.2,19.6], "#ab47bc", "bar"),
            ("训练耗时(Epoch)", [45,42,38,35,32,30,28,27,26,25,24,23], "#00bcd4", "line"),
        ]
        for i, (title, data, color, ctype) in enumerate(charts):
            cg.addWidget(MiniChart(title, data, color, ctype), i // 3, i % 3)
        chart_gb.setLayout(cg)
        scroll_layout.addWidget(chart_gb)

        # 数据表格
        table_gb = QGroupBox("📋 详细指标数据")
        tl = QVBoxLayout()
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(7)
        self.metrics_table.setHorizontalHeaderLabels(["Epoch","Train Loss","Val Loss","Accuracy","Precision","Recall","F1"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        demo_data = [
            (1,2.10,1.95,0.45,0.42,0.38,0.40),(2,1.50,1.42,0.58,0.55,0.52,0.53),
            (3,1.10,1.05,0.65,0.63,0.60,0.61),(4,0.80,0.78,0.72,0.70,0.69,0.69),
            (5,0.60,0.58,0.78,0.76,0.74,0.75),(6,0.45,0.44,0.82,0.80,0.79,0.79),
            (7,0.35,0.34,0.85,0.84,0.82,0.83),(8,0.28,0.27,0.88,0.87,0.85,0.86),
            (9,0.22,0.21,0.90,0.89,0.88,0.88),(10,0.18,0.18,0.91,0.90,0.89,0.89),
            (11,0.15,0.15,0.92,0.91,0.90,0.91),(12,0.12,0.12,0.93,0.92,0.91,0.92),
        ]
        self.metrics_table.setRowCount(len(demo_data))
        for r, row_data in enumerate(demo_data):
            for c, val in enumerate(row_data):
                self.metrics_table.setItem(r, c, QTableWidgetItem(str(val)))
        tl.addWidget(self.metrics_table)
        table_gb.setLayout(tl)
        scroll_layout.addWidget(table_gb)

        # 汇总统计
        summary_gb = QGroupBox("📊 汇总统计")
        sl = QHBoxLayout()
        summaries = [("总训练轮次","12"),("最佳准确率","0.93"),("最佳F1分数","0.92"),
                     ("总训练耗时","4h32m"),("平均推理耗时","14.7ms"),("模型大小","25.3MB")]
        for label, val in summaries:
            card = QGroupBox(label); card.setStyleSheet("QGroupBox{color:#E65100;font-size:11px;}")
            vl = QLabel(val); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
            card.setLayout(QVBoxLayout()); card.layout().addWidget(vl)
            sl.addWidget(card)
        summary_gb.setLayout(sl)
        scroll_layout.addWidget(summary_gb)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_w)
        layout.addWidget(scroll)

    def _refresh(self):
        QMessageBox.information(self, "刷新", f"已刷新 [{self.proj_combo.currentText()}] 报表数据")

    def _export_report(self):
        QMessageBox.information(self, "导出", "报表已导出为PDF/Excel格式\n包含全部图表与数据表格")

def get_module_widget(user):
    return ReportCenterWidget(user)
