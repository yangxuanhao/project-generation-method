from __future__ import annotations

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
    QComboBox, QListWidget, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import QTimer
from app.core.models import AnnotationTask
from app.ui.widgets import PanelCard, primary_button, InfoBox


class StreetViewPanel(QWidget):
    """实时街景路面裂缝标注舱。

    这里先做本地模拟实时街景：可导入街景图片，也可从内置街景序列逐帧切换。
    API 接入口只预留字段和测试按钮，暂不发起真实网络请求。
    """

    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.project_root = Path(project_root)
        self.canvas = canvas
        self.street_frames = sorted((self.project_root / 'assets' / 'streetview').glob('*.png'))
        self.frame_index = 0
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self.next_frame)

        layout = QVBoxLayout(self)
        card = PanelCard('实时街景标注舱')

        self.road_name = QLineEdit('G320示范街景路段')
        self.station = QLineEdit('K12+300')
        self.location_name = QLineEdit('武汉市东西湖区示范道路')
        self.lon = QLineEdit('114.305678')
        self.lat = QLineEdit('30.572123')
        self.direction = QComboBox(); self.direction.addItems(['上行', '下行', '东向西', '西向东', '南向北', '北向南'])
        self.road_level = QComboBox(); self.road_level.addItems(['城市主干路', '城市次干路', '一般公路', '高速公路', '桥面铺装'])
        self.note = QLineEdit('街景模拟帧，用于路面裂缝快速预标注')

        for label, widget in [
            ('路段名称', self.road_name),
            ('当前桩号', self.station),
            ('位置说明', self.location_name),
            ('经度', self.lon),
            ('纬度', self.lat),
            ('道路方向', self.direction),
            ('道路等级', self.road_level),
            ('备注', self.note),
        ]:
            card.layout.addWidget(QLabel(label))
            card.layout.addWidget(widget)

        import_btn = primary_button('导入街景图并创建任务')
        import_btn.clicked.connect(self.import_street_image)
        sample_btn = QPushButton('打开真实街景样例')
        sample_btn.clicked.connect(self.open_current_sample)
        prev_btn = QPushButton('上一帧')
        prev_btn.clicked.connect(self.prev_frame)
        next_btn = QPushButton('下一帧')
        next_btn.clicked.connect(self.next_frame)

        card.layout.addWidget(import_btn)
        card.layout.addWidget(sample_btn)

        frame_row = QHBoxLayout()
        frame_row.addWidget(prev_btn)
        frame_row.addWidget(next_btn)
        card.layout.addLayout(frame_row)

        self.live_btn = QPushButton('开始模拟实时街景')
        self.live_btn.clicked.connect(self.toggle_live)
        card.layout.addWidget(self.live_btn)

        api_title = QLabel('API 接入口（暂不接入，仅预留配置）')
        card.layout.addWidget(api_title)
        self.api_url = QLineEdit('https://your-api-endpoint.example/streetview')
        self.api_key = QLineEdit('')
        self.api_key.setPlaceholderText('API Key / Token')
        card.layout.addWidget(QLabel('接口地址'))
        card.layout.addWidget(self.api_url)
        card.layout.addWidget(QLabel('API Key'))
        card.layout.addWidget(self.api_key)
        test_api = QPushButton('测试连接（占位，不发起网络请求）')
        test_api.clicked.connect(self.test_api_placeholder)
        card.layout.addWidget(test_api)

        self.frame_list = QListWidget()
        self.frame_list.setMaximumHeight(120)
        self.frame_list.itemClicked.connect(self.pick_frame)
        card.layout.addWidget(QLabel('街景帧列表'))
        card.layout.addWidget(self.frame_list)

        self.info = InfoBox('街景标注流程：导入/打开街景帧 → 自动标注舱识别裂缝 → 浏览模式人工修正 → 宽度卡尺估算。')
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.refresh_frames()

    def refresh_frames(self):
        self.frame_list.clear()
        for p in self.street_frames:
            self.frame_list.addItem(p.name)

    def _create_task(self, image_path: str):
        station = self.station.text().strip() or 'K0+000'
        task = AnnotationTask(
            road_name=self.road_name.text().strip() or '街景路段',
            image_path=str(image_path),
            pavement_type='街景路面',
            station_start=station,
            station_end=station,
            lane='街景采集车道',
            location_name=self.location_name.text().strip(),
            longitude=self.lon.text().strip(),
            latitude=self.lat.text().strip(),
            road_level=self.road_level.currentText(),
            direction=self.direction.currentText(),
            section_note=self.note.text().strip(),
            source_type='街景路面影像',
            annotator='当前用户',
            status='街景待标注',
        )
        self.state.add_task(task)
        self.storage.upsert_task(task)
        self.info.setText(
            f'已创建街景标注任务：{task.road_name}\n'
            f'位置：{task.location_name}\n'
            f'坐标：{task.latitude}, {task.longitude}\n'
            f'影像：{Path(task.image_path).name}\n'
            '可进入自动标注舱执行裂缝识别。'
        )

    def import_street_image(self):
        path, _ = QFileDialog.getOpenFileName(self, '导入街景路面图', str(self.project_root), 'Images (*.png *.jpg *.jpeg *.bmp)')
        if path:
            self._create_task(path)

    def open_current_sample(self):
        if not self.street_frames:
            QMessageBox.warning(self, '缺少街景样例', 'assets/streetview 下没有街景样例图')
            return
        self._create_task(str(self.street_frames[self.frame_index]))

    def pick_frame(self, item):
        row = self.frame_list.currentRow()
        if 0 <= row < len(self.street_frames):
            self.frame_index = row
            self.open_current_sample()

    def next_frame(self):
        if not self.street_frames:
            return
        self.frame_index = (self.frame_index + 1) % len(self.street_frames)
        self.station.setText(f'K12+{300 + self.frame_index * 50}')
        self.open_current_sample()

    def prev_frame(self):
        if not self.street_frames:
            return
        self.frame_index = (self.frame_index - 1) % len(self.street_frames)
        self.station.setText(f'K12+{300 + self.frame_index * 50}')
        self.open_current_sample()

    def toggle_live(self):
        if self.timer.isActive():
            self.timer.stop()
            self.state.street_view_live = False
            self.live_btn.setText('开始模拟实时街景')
            QMessageBox.information(self, '实时街景', '已停止模拟实时街景。')
        else:
            self.timer.start()
            self.state.street_view_live = True
            self.live_btn.setText('停止模拟实时街景')
            QMessageBox.information(self, '实时街景', '已开始模拟连续街景帧。每一帧都会创建一个街景标注任务，可进入自动标注舱识别裂缝。')

    def test_api_placeholder(self):
        QMessageBox.information(
            self,
            'API 接入口',
            '当前仅预留 API 接入口，不会发起真实网络请求。\n'
            f'接口地址：{self.api_url.text().strip()}\n'
            '后续可接入街景采集车、巡检平台或第三方街景服务。'
        )
