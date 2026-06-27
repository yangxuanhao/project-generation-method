"""可视化编排画布 - 拖拽节点、连线、分组、对齐布局"""
from PyQt6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QMenu, QInputDialog, QVBoxLayout, QHBoxLayout, QPushButton, QToolBar)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QLineF
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor,
    QFont, QLinearGradient, QCursor, QAction)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid, math

NODE_COLORS = {
    "数据预处理": ("#1565c0", "#1e88e5"),
    "传统机器学习": ("#00838f", "#00acc1"),
    "深度学习": ("#6a1b9a", "#8e24aa"),
    "推理": ("#e65100", "#fb8c00"),
    "分支判断": ("#2e7d32", "#43a047"),
    "循环": ("#c62828", "#e53935"),
    "数据输出": ("#37474f", "#546e7a"),
}

@dataclass
class CanvasNode:
    nid: str; node_type: str; label: str; x: float = 0; y: float = 0
    w: float = 140; h: float = 70; config: dict = field(default_factory=dict)

@dataclass
class CanvasEdge:
    eid: str; source: str; target: str; label: str = ""

class AINodeItem(QGraphicsRectItem):
    def __init__(self, node: CanvasNode, parent=None):
        super().__init__(0, 0, node.w, node.h, parent)
        self.node = node; self.nid = node.nid
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        colors = NODE_COLORS.get(node.node_type, ("#555", "#777"))
        self._bg_color = QColor(colors[0]); self._hover_color = QColor(colors[1])
        self.setPos(node.x, node.y); self.setZValue(10)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect(); is_sel = self.isSelected()
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, self._hover_color if is_sel else self._bg_color)
        gradient.setColorAt(1, QColor(self._bg_color.red()//2, self._bg_color.green()//2, self._bg_color.blue()//2))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#FF8F00") if is_sel else QColor("#FFD54F"), 3 if is_sel else 1.5))
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QPen(QColor("white")))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        painter.drawText(QRectF(4, 8, rect.width()-8, 22), Qt.AlignmentFlag.AlignCenter, self.node.label)
        painter.setPen(QPen(QColor("#E0E0E0")))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(QRectF(4, 30, rect.width()-8, 18), Qt.AlignmentFlag.AlignCenter, self.node.node_type)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view: view._on_node_moved()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        text, ok = QInputDialog.getText(None, "编辑节点", "节点标签:", text=self.node.label)
        if ok and text: self.node.label = text; self.update()

    def contextMenuEvent(self, event):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        menu = QMenu()
        menu.addAction("✎ 编辑标签", lambda: self.mouseDoubleClickEvent(None))
        if view:
            menu.addAction("📋 复制节点", lambda: view._copy_node_safe(self))
            menu.addAction("🗑 删除节点", lambda: view._remove_node_safe(self.nid))
            menu.addSeparator()
            menu.addAction("🔗 从此节点连线", lambda: view._start_connect_from(self))
        menu.addSeparator()
        menu.addAction("⬆ 置顶", lambda: self.setZValue(self.zValue() + 100))
        menu.exec(event.screenPos())

class EdgeItem(QGraphicsLineItem):
    def __init__(self, source: AINodeItem, target: AINodeItem, edge: CanvasEdge):
        super().__init__()
        self._src = source; self._tgt = target; self.edge = edge
        self.setPen(QPen(QColor("#FF8F00"), 2.5, Qt.PenStyle.SolidLine))
        self.setZValue(5)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._update_line()

    def _update_line(self):
        try:
            sr = self._src.sceneBoundingRect()
            tr = self._tgt.sceneBoundingRect()
            self.setLine(QLineF(sr.center().x(), sr.bottom(),
                                tr.center().x(), tr.top()))
        except (RuntimeError, AttributeError):
            pass

    def contextMenuEvent(self, event):
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        menu = QMenu()
        if view:
            menu.addAction("🗑 删除连线", lambda: view._delete_edge_safe(self))
        menu.exec(event.screenPos())

class ModelCanvas(QGraphicsView):
    flow_changed = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -1500, 5000, 4000)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._nodes: Dict[str, AINodeItem] = {}
        self._edges: Dict[str, EdgeItem] = {}
        self._connect_mode = False; self._connect_source: Optional[AINodeItem] = None
        self._undo_stack: List[dict] = []; self._redo_stack: List[dict] = []
        self._drag_pos = None
        self.setMouseTracking(True)

    def add_node(self, node_type: str, label: str, x: float = 0, y: float = 0) -> str:
        import random as _r
        node = CanvasNode(nid=uuid.uuid4().hex[:8], node_type=node_type, label=label,
                          x=x or _r.randint(0, 400), y=y or _r.randint(0, 300))
        item = AINodeItem(node); self._scene.addItem(item)
        self._nodes[node.nid] = item
        self._push_undo("add", node.nid)
        self.flow_changed.emit()
        return node.nid

    def _remove_node_safe(self, nid: str):
        try:
            item = self._nodes.get(nid)
            if not item: return
            for eid in list(self._edges.keys()):
                e = self._edges[eid]
                if e._src.nid == nid or e._tgt.nid == nid:
                    self._scene.removeItem(e); del self._edges[eid]
            self._push_undo("del", nid)
            self._scene.removeItem(item); del self._nodes[nid]
            self.flow_changed.emit()
        except Exception as e:
            self.status_message.emit(f"删除失败: {e}")

    def _start_connect_from(self, source_item: AINodeItem):
        self._connect_mode = True; self._connect_source = source_item
        source_item.setSelected(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.status_message.emit(f"🔗 连线模式：请点击目标节点（源：{source_item.node.label}）")

    def connect_nodes(self):
        try:
            selected = [it for it in self._scene.selectedItems() if isinstance(it, AINodeItem)]
            if len(selected) != 2:
                self.status_message.emit(f"⚠ 请先选中2个节点再连线（当前选中{len(selected)}个）| 方法：Ctrl+点击选2个节点 → 点连线按钮")
                return
            self._make_edge(selected[0], selected[1])
        except Exception as e:
            self.status_message.emit(f"连线失败: {e}")

    def _make_edge(self, src: AINodeItem, tgt: AINodeItem):
        if src.nid == tgt.nid:
            self.status_message.emit("⚠ 不能连接自身"); return
        for e in self._edges.values():
            if e._src.nid == src.nid and e._tgt.nid == tgt.nid:
                self.status_message.emit("⚠ 这两个节点已有连线"); return
        eid = uuid.uuid4().hex[:8]
        edge = CanvasEdge(eid=eid, source=src.nid, target=tgt.nid)
        item = EdgeItem(src, tgt, edge)
        self._scene.addItem(item); self._edges[eid] = item
        self._connect_mode = False; self._connect_source = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        src.setSelected(False); tgt.setSelected(False)
        self.status_message.emit(f"✅ 连线成功：{src.node.label} → {tgt.node.label}")
        self.flow_changed.emit()

    def _delete_edge_safe(self, edge_item: EdgeItem):
        try:
            eid = edge_item.edge.eid
            if eid in self._edges:
                self._scene.removeItem(edge_item); del self._edges[eid]
                self.status_message.emit("🗑 连线已删除")
                self.flow_changed.emit()
        except Exception as e:
            self.status_message.emit(f"删除连线失败: {e}")

    def _on_node_moved(self):
        for e in self._edges.values():
            try: e._update_line()
            except: pass

    def _copy_node_safe(self, item: AINodeItem):
        self.add_node(item.node.node_type, item.node.label + "_副本",
                      item.node.x + 50, item.node.y + 50)

    def auto_layout(self):
        try:
            from core.algorithms import ForceDirectedLayout, LayoutNode
            nl = [LayoutNode(nid=n.nid, x=n.node.x, y=n.node.y) for n in self._nodes.values()]
            el = [(e._src.nid, e._tgt.nid) for e in self._edges.values()]
            result = ForceDirectedLayout(width=2000, height=1500).layout(nl, el)
            for ln in result:
                if ln.nid in self._nodes:
                    self._nodes[ln.nid].setPos(ln.x, ln.y)
            for e in self._edges.values(): e._update_line()
            self.flow_changed.emit()
        except Exception as e:
            self.status_message.emit(f"布局失败: {e}")

    def align_nodes(self, mode: str = "hcenter"):
        selected = [it for it in self._scene.selectedItems() if isinstance(it, AINodeItem)]
        if len(selected) < 2:
            self.status_message.emit("⚠ 请至少选中2个节点")
            return
        if mode == "hcenter":
            avg = sum(it.x() + it.rect().width()/2 for it in selected) / len(selected)
            for it in selected: it.setX(avg - it.rect().width()/2)
        elif mode == "vcenter":
            avg = sum(it.y() + it.rect().height()/2 for it in selected) / len(selected)
            for it in selected: it.setY(avg - it.rect().height()/2)
        elif mode == "grid":
            cols = math.ceil(math.sqrt(len(selected)))
            for i, it in enumerate(sorted(selected, key=lambda x: x.y())):
                it.setPos((i % cols) * 180, (i // cols) * 100)
        for e in self._edges.values(): e._update_line()
        self.status_message.emit(f"✅ {len(selected)}个节点已对齐")
        self.flow_changed.emit()

    def clear_all(self):
        for e in list(self._edges.values()): self._scene.removeItem(e)
        for n in list(self._nodes.values()): self._scene.removeItem(n)
        self._nodes.clear(); self._edges.clear()
        self.flow_changed.emit()

    def get_flow_data(self) -> dict:
        nodes = [{"id": n.nid, "type": n.node.node_type, "label": n.node.label,
                  "x": n.node.x, "y": n.node.y} for n in self._nodes.values()]
        edges = [{"id": e.edge.eid, "source": e._src.nid, "target": e._tgt.nid}
                 for e in self._edges.values()]
        return {"nodes": nodes, "edges": edges}

    def load_flow_data(self, data: dict):
        self.clear_all()
        for nd in data.get("nodes", []):
            node = CanvasNode(nid=nd["id"], node_type=nd["type"], label=nd["label"],
                              x=nd["x"], y=nd["y"])
            item = AINodeItem(node); self._scene.addItem(item)
            self._nodes[node.nid] = item
        for ed in data.get("edges", []):
            src = self._nodes.get(ed["source"]); tgt = self._nodes.get(ed["target"])
            if src and tgt:
                edge = CanvasEdge(eid=ed["id"], source=ed["source"], target=ed["target"])
                item = EdgeItem(src, tgt, edge)
                self._scene.addItem(item); self._edges[edge.eid] = item

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._drag_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor); return
        if event.button() == Qt.MouseButton.LeftButton:
            pt = event.position().toPoint()
            item = self.itemAt(pt)
            if self._connect_mode and isinstance(item, AINodeItem):
                if item is not self._connect_source:
                    try: self._make_edge(self._connect_source, item)
                    except Exception as e: self.status_message.emit(f"连线异常: {e}")
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.position().toPoint() - self._drag_pos
            self._drag_pos = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y()); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._drag_pos = None; self.setCursor(Qt.CursorShape.ArrowCursor); return
        if self._connect_mode and event.button() == Qt.MouseButton.RightButton:
            self._connect_mode = False; self._connect_source = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_message.emit("❌ 已取消连线"); return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for it in list(self._scene.selectedItems()):
                if isinstance(it, AINodeItem):
                    self._remove_node_safe(it.nid)
                elif isinstance(it, EdgeItem):
                    self._delete_edge_safe(it)
        elif event.key() == Qt.Key.Key_Escape:
            if self._connect_mode:
                self._connect_mode = False; self._connect_source = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.status_message.emit("❌ 连线模式已取消")
        elif event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.redo()
        else:
            super().keyPressEvent(event)

    def _push_undo(self, action: str, target: str):
        self._undo_stack.append({"act": action, "tgt": target, "data": self.get_flow_data()})
        if len(self._undo_stack) > 50: self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if self._undo_stack:
            item = self._undo_stack.pop()
            self._redo_stack.append({"data": self.get_flow_data()})
            self.load_flow_data(item["data"])
            self.flow_changed.emit(); self.status_message.emit("↩ 已撤销")

    def redo(self):
        if self._redo_stack:
            item = self._redo_stack.pop()
            self._undo_stack.append({"data": self.get_flow_data()})
            self.load_flow_data(item["data"])
            self.flow_changed.emit(); self.status_message.emit("↪ 已重做")
