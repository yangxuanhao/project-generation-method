from __future__ import annotations

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
    QComboBox, QListWidget, QMessageBox
)
from app.core.models import AnnotationTask
from app.ui.widgets import PanelCard, primary_button, InfoBox


class ImageTaskPanel(QWidget):
    def __init__(self, state, storage, project_root, canvas=None, parent=None):
        super().__init__(parent)
        self.state = state
        self.storage = storage
        self.project_root = Path(project_root)
        self.canvas = canvas
        layout = QVBoxLayout(self)
        card = PanelCard('影像任务舱')

        self.road = QLineEdit('G320示范路段')
        self.station_start = QLineEdit('K12+000')
        self.station_end = QLineEdit('K12+100')
        self.location_name = QLineEdit('武汉市东西湖区示范路段')
        self.longitude = QLineEdit('114.305678')
        self.latitude = QLineEdit('30.572123')
        self.direction = QComboBox(); self.direction.addItems(['上行', '下行', '东向西', '西向东', '南向北', '北向南'])
        self.road_level = QComboBox(); self.road_level.addItems(['城市主干路', '城市次干路', '一般公路', '高速公路', '桥面铺装'])
        self.section_note = QLineEdit('常规路面巡检影像')
        self.pavement = QComboBox(); self.pavement.addItems(['沥青路面', '水泥混凝土路面', '桥面铺装', '隧道路面'])
        self.lane = QComboBox(); self.lane.addItems(['上行一车道', '上行二车道', '下行一车道', '下行二车道', '匝道'])

        for label, widget in [
            ('道路名称', self.road),
            ('起点桩号', self.station_start),
            ('终点桩号', self.station_end),
            ('位置说明', self.location_name),
            ('经度', self.longitude),
            ('纬度', self.latitude),
            ('道路方向', self.direction),
            ('道路等级', self.road_level),
            ('路面类型', self.pavement),
            ('车道', self.lane),
            ('路段备注', self.section_note),
        ]:
            card.layout.addWidget(QLabel(label))
            card.layout.addWidget(widget)

        import_btn = primary_button('导入本地路面影像并创建任务')
        sample_btn = QPushButton('打开更真实的内置样例影像')
        save_meta = QPushButton('更新当前任务路段信息')
        refresh_btn = QPushButton('刷新任务列表')
        delete_line = QPushButton('删除选中标注线')
        import_btn.clicked.connect(self.import_image)
        sample_btn.clicked.connect(self.open_sample)
        save_meta.clicked.connect(self.update_current_metadata)
        refresh_btn.clicked.connect(self.refresh_list)
        delete_line.clicked.connect(self.delete_selected_line)
        card.layout.addWidget(import_btn)
        card.layout.addWidget(sample_btn)
        card.layout.addWidget(save_meta)
        card.layout.addWidget(delete_line)
        card.layout.addWidget(refresh_btn)

        self.task_list = QListWidget()
        self.task_list.setMaximumHeight(150)
        self.task_list.itemClicked.connect(self.select_task)
        card.layout.addWidget(QLabel('任务卡片'))
        card.layout.addWidget(self.task_list)
        self.info = InfoBox('导入影像后会生成标注任务；每个路段可填写位置、坐标、方向、等级和备注。')
        card.layout.addWidget(self.info)
        layout.addWidget(card)
        self.state.task_changed.connect(self.refresh_list)
        self.refresh_list()

    def import_image(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择路面影像', str(self.project_root), 'Images (*.png *.jpg *.jpeg *.bmp)')
        if path:
            self.create_task(path)

    def open_sample(self):
        samples = sorted((self.project_root / 'assets' / 'samples').glob('*.png'))
        if not samples:
            QMessageBox.warning(self, '缺少样例', '未找到样例影像')
            return
        row = max(0, len(self.state.tasks) % len(samples))
        self.create_task(str(samples[row]))

    def create_task(self, image_path):
        task = AnnotationTask(
            road_name=self.road.text().strip() or '未命名道路',
            image_path=str(image_path),
            pavement_type=self.pavement.currentText(),
            station_start=self.station_start.text().strip() or 'K0+000',
            station_end=self.station_end.text().strip() or 'K0+100',
            lane=self.lane.currentText(),
            location_name=self.location_name.text().strip(),
            longitude=self.longitude.text().strip(),
            latitude=self.latitude.text().strip(),
            road_level=self.road_level.currentText(),
            direction=self.direction.currentText(),
            section_note=self.section_note.text().strip(),
            source_type='普通路面影像',
            annotator='当前用户',
            status='待标注',
        )
        self.state.add_task(task)
        self.storage.upsert_task(task)
        self.info.setText(
            f'已创建任务：{task.road_name}\n'
            f'位置：{task.location_name}\n'
            f'坐标：{task.latitude}, {task.longitude}\n'
            f'影像：{Path(task.image_path).name}\n'
            '建议流程：比例标定 → 自动识别/人工描绘 → 宽度估算 → 复核。'
        )

    def update_current_metadata(self):
        task = self.state.current_task
        if not task:
            return
        task.road_name = self.road.text().strip() or task.road_name
        task.station_start = self.station_start.text().strip() or task.station_start
        task.station_end = self.station_end.text().strip() or task.station_end
        task.location_name = self.location_name.text().strip()
        task.longitude = self.longitude.text().strip()
        task.latitude = self.latitude.text().strip()
        task.direction = self.direction.currentText()
        task.road_level = self.road_level.currentText()
        task.pavement_type = self.pavement.currentText()
        task.lane = self.lane.currentText()
        task.section_note = self.section_note.text().strip()
        task.touch()
        self.storage.upsert_task(task)
        self.refresh_list()
        QMessageBox.information(self, '路段信息已更新', '当前任务的位置、坐标、方向和备注已保存。')

    def delete_selected_line(self):
        if not self.canvas:
            return
        ok, msg = self.canvas.delete_selected_any_annotation()
        self.refresh_list()
        QMessageBox.information(self, '删除标注线', msg)

    def refresh_list(self):
        self.task_list.clear()
        for task in self.state.tasks:
            self.task_list.addItem(
                f'{task.road_name}｜{task.station_start}-{task.station_end}｜{task.location_name}｜裂缝{len(task.cracks)}｜{task.status}'
            )

    def select_task(self, item):
        row = self.task_list.currentRow()
        if 0 <= row < len(self.state.tasks):
            task = self.state.tasks[row]
            self.state.set_current_task(task)
            self.road.setText(task.road_name)
            self.station_start.setText(task.station_start)
            self.station_end.setText(task.station_end)
            self.location_name.setText(task.location_name)
            self.longitude.setText(task.longitude)
            self.latitude.setText(task.latitude)
            self.direction.setCurrentText(task.direction)
            self.road_level.setCurrentText(task.road_level)
            self.pavement.setCurrentText(task.pavement_type)
            self.lane.setCurrentText(task.lane)
            self.section_note.setText(task.section_note)
            self.info.setText(
                f'当前任务：{task.road_name}\n'
                f'位置：{task.location_name}\n'
                f'坐标：{task.latitude}, {task.longitude}\n'
                f'影像：{Path(task.image_path).name}\n'
                '模式建议：先标定比例尺，再自动识别或描绘裂缝。'
            )
