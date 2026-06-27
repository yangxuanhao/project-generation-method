from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import pyqtSignal


class ObjectListWidget(QTableWidget):
    object_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__(0, 7)
        self.setHorizontalHeaderLabels(['ID', '标签', '坐标', '宽高', '置信度', '来源', '状态'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setVisible(False)
        self.cellClicked.connect(self._cell_clicked)

    def set_objects(self, rows: list[dict]):
        self.setRowCount(len(rows))
        self._ids = []
        for r, obj in enumerate(rows):
            self._ids.append(int(obj.get('id')))
            vals = [
                obj.get('id'), obj.get('label'), f"{float(obj.get('x',0)):.0f},{float(obj.get('y',0)):.0f}",
                f"{float(obj.get('w',0)):.0f}×{float(obj.get('h',0)):.0f}", f"{float(obj.get('confidence',0))*100:.0f}%", obj.get('source'), obj.get('status')
            ]
            for c, v in enumerate(vals):
                self.setItem(r, c, QTableWidgetItem(str(v)))

    def _cell_clicked(self, row: int, col: int):
        if 0 <= row < len(getattr(self, '_ids', [])):
            self.object_selected.emit(self._ids[row])
