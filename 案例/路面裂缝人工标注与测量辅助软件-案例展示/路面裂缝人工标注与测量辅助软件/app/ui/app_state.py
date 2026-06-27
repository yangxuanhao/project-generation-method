from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, List
from app.core.models import AnnotationTask, CrackObject
from app.core.snap import CrackSnapAssistant


class AppState(QObject):
    task_changed = pyqtSignal()
    selection_changed = pyqtSignal()
    mode_changed = pyqtSignal(str)
    message = pyqtSignal(str)
    view_flags_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.tasks: List[AnnotationTask] = []
        self.current_task: Optional[AnnotationTask] = None
        self.selected_crack_id: Optional[str] = None
        self.mode: str = '浏览'
        self.snap_assistant = CrackSnapAssistant(False, 10)
        self.temporary_points = []
        self.width_pending_point = None
        self.region_pending_points = []
        self.show_scale_ruler = True
        self.show_reference_grid = True
        self.reference_grid_opacity = 38   # 0-100，画在影像上的网格透明度
        self.overlay_line_opacity = 100
        self.street_view_live = False

    def set_tasks(self, tasks: List[AnnotationTask]):
        self.tasks = tasks
        if tasks and self.current_task is None:
            self.current_task = tasks[0]
        self.task_changed.emit()

    def set_current_task(self, task: Optional[AnnotationTask]):
        self.current_task = task
        self.selected_crack_id = None
        self.temporary_points.clear()
        self.width_pending_point = None
        self.region_pending_points.clear()
        self.task_changed.emit()
        self.selection_changed.emit()

    def set_mode(self, mode: str):
        self.mode = mode
        self.temporary_points.clear()
        self.width_pending_point = None
        self.region_pending_points.clear()
        self.mode_changed.emit(mode)
        self.message.emit(f'当前模式：{mode}')

    def set_show_scale_ruler(self, flag: bool):
        self.show_scale_ruler = bool(flag)
        self.view_flags_changed.emit()

    def set_show_reference_grid(self, flag: bool):
        self.show_reference_grid = bool(flag)
        self.view_flags_changed.emit()

    def set_reference_grid_opacity(self, value: int):
        self.reference_grid_opacity = max(0, min(100, int(value)))
        self.view_flags_changed.emit()

    def set_overlay_line_opacity(self, value: int):
        self.overlay_line_opacity = max(15, min(100, int(value)))
        self.view_flags_changed.emit()

    def selected_crack(self) -> Optional[CrackObject]:
        if not self.current_task or not self.selected_crack_id:
            return None
        for crack in self.current_task.cracks:
            if crack.crack_id == self.selected_crack_id:
                return crack
        return None

    def select_crack(self, crack_id: Optional[str]):
        self.selected_crack_id = crack_id
        self.selection_changed.emit()
        if crack_id:
            self.message.emit(f'已选中 {crack_id}')

    def add_task(self, task: AnnotationTask):
        self.tasks.append(task)
        self.set_current_task(task)
        self.message.emit(f'已创建任务：{task.road_name}')
