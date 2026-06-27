from __future__ import annotations
from math import cos, sin, pi
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient


def _color(value: str | QColor) -> QColor:
    return value if isinstance(value, QColor) else QColor(value)


class DonutGauge(QWidget):
    def __init__(self, title='健康度', value=0, suffix='分', parent=None):
        super().__init__(parent)
        self.title = title
        self.value = float(value)
        self.suffix = suffix
        self.setMinimumSize(180, 180)

    def set_value(self, value: float):
        self.value = float(value)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(18, 18, self.width() - 36, self.height() - 36)
        line_w = max(14, min(self.width(), self.height()) // 13)
        p.setPen(QPen(QColor('#e2e8f0'), line_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 0, 360 * 16)
        val = max(0, min(100, self.value))
        if val >= 90: c = QColor('#16a34a')
        elif val >= 80: c = QColor('#2563eb')
        elif val >= 70: c = QColor('#f59e0b')
        else: c = QColor('#dc2626')
        p.setPen(QPen(c, line_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 90 * 16, int(-360 * 16 * val / 100))
        p.setPen(QColor('#0f172a'))
        font = QFont(); font.setBold(True); font.setPointSize(26); p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{val:.1f}")
        font.setPointSize(11); font.setBold(False); p.setFont(font); p.setPen(QColor('#64748b'))
        p.drawText(QRectF(0, self.height()/2+34, self.width(), 24), Qt.AlignmentFlag.AlignCenter, f"{self.title}{self.suffix}")


class MiniBarChart(QWidget):
    barClicked = pyqtSignal(str)
    def __init__(self, title='分布', data: list[tuple[str, float]] | None = None, unit='', parent=None):
        super().__init__(parent)
        self.title = title
        self.data = data or []
        self.unit = unit
        self.setMinimumHeight(190)
        self.setMouseTracking(True)
        self._bar_rects: list[tuple[QRectF, str]] = []

    def set_data(self, data: list[tuple[str, float]], title: str | None = None, unit: str | None = None):
        self.data = data
        if title is not None: self.title = title
        if unit is not None: self.unit = unit
        self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        for rect, label in self._bar_rects:
            if rect.contains(pos):
                self.barClicked.emit(label)
                break

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('transparent'))
        p.setPen(QColor('#0f172a'))
        font = QFont(); font.setBold(True); font.setPointSize(11); p.setFont(font)
        p.drawText(8, 20, self.title)
        if not self.data:
            p.setPen(QColor('#94a3b8')); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '暂无数据')
            return
        left, top, right, bottom = 18, 42, 14, 32
        chart = QRectF(left, top, self.width()-left-right, self.height()-top-bottom)
        maxv = max(v for _, v in self.data) or 1
        self._bar_rects.clear()
        n = len(self.data)
        gap = 8 if n < 8 else 4
        bw = max(12, (chart.width() - gap*(n-1)) / n)
        for i, (label, val) in enumerate(self.data):
            h = chart.height() * val / maxv
            x = chart.left() + i * (bw + gap)
            y = chart.bottom() - h
            rect = QRectF(x, y, bw, h)
            self._bar_rects.append((rect.adjusted(-2, -2, 2, 2), label))
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            grad.setColorAt(0, QColor('#38bdf8'))
            grad.setColorAt(1, QColor('#2563eb'))
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 6, 6)
            p.setPen(QColor('#334155'))
            p.setFont(QFont('', 8))
            p.drawText(QRectF(x-10, chart.bottom()+4, bw+20, 20), Qt.AlignmentFlag.AlignCenter, label[:10])
            p.setPen(QColor('#0f172a'))
            p.drawText(QRectF(x-10, y-20, bw+20, 16), Qt.AlignmentFlag.AlignCenter, f"{int(val) if float(val).is_integer() else round(val,1)}{self.unit}")


class TrendLine(QWidget):
    def __init__(self, title='趋势', data: list[tuple[str, float]] | None = None, unit='', parent=None):
        super().__init__(parent); self.title=title; self.data=data or []; self.unit=unit; self.setMinimumHeight(160)

    def set_data(self, data, title=None, unit=None):
        self.data=data
        if title is not None: self.title=title
        if unit is not None: self.unit=unit
        self.update()

    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor('#0f172a')); font=QFont(); font.setBold(True); font.setPointSize(11); p.setFont(font); p.drawText(8,20,self.title)
        if len(self.data)<2:
            p.setPen(QColor('#94a3b8')); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '暂无趋势数据'); return
        left,top,right,bottom=20,44,18,30; rect=QRectF(left,top,self.width()-left-right,self.height()-top-bottom)
        p.setPen(QPen(QColor('#e2e8f0'),1));
        for i in range(4):
            y=rect.top()+i*rect.height()/3; p.drawLine(QPointF(rect.left(),y), QPointF(rect.right(),y))
        vals=[v for _,v in self.data]; mn=min(vals); mx=max(vals); span=max(1,mx-mn)
        pts=[]
        for i,(label,val) in enumerate(self.data):
            x=rect.left()+i*rect.width()/(len(self.data)-1); y=rect.bottom()-(val-mn)*rect.height()/span; pts.append(QPointF(x,y))
        path=QPainterPath(pts[0])
        for pt in pts[1:]: path.lineTo(pt)
        p.setPen(QPen(QColor('#2563eb'),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); p.drawPath(path)
        p.setBrush(QColor('#2563eb')); p.setPen(Qt.PenStyle.NoPen)
        for pt in pts: p.drawEllipse(pt,4,4)
        p.setPen(QColor('#475569')); p.setFont(QFont('',8))
        for i,(label,val) in enumerate(self.data):
            if i in (0,len(self.data)-1) or len(self.data)<=6:
                p.drawText(QRectF(pts[i].x()-30, rect.bottom()+4, 60, 18), Qt.AlignmentFlag.AlignCenter, label)


class PipelineWidget(QWidget):
    stageClicked = pyqtSignal(str)
    def __init__(self, stages: list[tuple[str, int]] | None = None, parent=None):
        super().__init__(parent); self.stages=stages or []; self.setMinimumHeight(120); self._items=[]

    def set_stages(self, stages): self.stages=stages; self.update()

    def mousePressEvent(self, event):
        pos=event.position()
        for rect,name in self._items:
            if rect.contains(pos): self.stageClicked.emit(name); break

    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.stages:
            p.setPen(QColor('#94a3b8')); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '暂无生产流数据'); return
        margin=18; y=30; h=54; gap=10; n=len(self.stages); w=(self.width()-2*margin-gap*(n-1))/n
        self._items=[]
        for i,(name,count) in enumerate(self.stages):
            x=margin+i*(w+gap); rect=QRectF(x,y,w,h); self._items.append((rect,name))
            p.setPen(Qt.PenStyle.NoPen)
            tone=['#dbeafe','#e0f2fe','#fef3c7','#fee2e2','#dcfce7','#ede9fe'][i%6]
            p.setBrush(QColor(tone)); p.drawRoundedRect(rect,14,14)
            p.setPen(QColor('#0f172a')); font=QFont(); font.setBold(True); font.setPointSize(15); p.setFont(font)
            p.drawText(QRectF(x,y+8,w,20), Qt.AlignmentFlag.AlignCenter, str(count))
            font.setBold(False); font.setPointSize(9); p.setFont(font); p.setPen(QColor('#475569'))
            p.drawText(QRectF(x+4,y+32,w-8,18), Qt.AlignmentFlag.AlignCenter, name)
            if i<n-1:
                p.setPen(QPen(QColor('#94a3b8'),2,Qt.PenStyle.DashLine));
                p.drawLine(QPointF(x+w+2,y+h/2), QPointF(x+w+gap-2,y+h/2))


class RiskHeatmap(QWidget):
    cellClicked = pyqtSignal(str)
    def __init__(self, title='风险热力图', data: dict[str, int] | None = None, parent=None):
        super().__init__(parent); self.title=title; self.data=data or {}; self._cells=[]; self.setMinimumHeight(236)

    def set_data(self, data): self.data=data; self.update()

    def mousePressEvent(self, event):
        for rect,name in self._cells:
            if rect.contains(event.position()): self.cellClicked.emit(name); break

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor('#0f172a')); font=QFont(); font.setBold(True); font.setPointSize(11); p.setFont(font); p.drawText(8,20,self.title)
        if not self.data:
            p.setPen(QColor('#94a3b8')); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '暂无风险数据'); return
        keys=list(self.data.keys()); maxv=max(self.data.values()) or 1
        cols = 2 if self.width() < 420 else 3
        gap=8; left=10; top=40; cw=(self.width()-left*2-gap*(cols-1))/cols; ch=54; self._cells=[]
        for idx,k in enumerate(keys):
            row=idx//cols; col=idx%cols; x=left+col*(cw+gap); y=top+row*(ch+gap); rect=QRectF(x,y,cw,ch); self._cells.append((rect,k))
            v=self.data[k]; ratio=v/maxv
            if ratio>0.66: color=QColor('#fecaca')
            elif ratio>0.33: color=QColor('#fde68a')
            else: color=QColor('#dbeafe')
            p.setBrush(color); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect,12,12)
            p.setPen(QColor('#0f172a')); f=QFont(); f.setBold(True); f.setPointSize(13); p.setFont(f); p.drawText(QRectF(x+10,y+8,40,20), Qt.AlignmentFlag.AlignLeft, str(v))
            p.setPen(QColor('#334155')); p.setFont(QFont('Microsoft YaHei',8))
            p.drawText(QRectF(x+52,y+6,cw-58,ch-10), int(Qt.AlignmentFlag.AlignVCenter.value | Qt.AlignmentFlag.AlignLeft.value | Qt.TextFlag.TextWordWrap.value), k)


class WorkflowCard(QFrame):
    clicked = pyqtSignal(str)
    def __init__(self, title: str, value: str, desc: str, action: str = '', tone='blue', parent=None):
        super().__init__(parent)
        self.action=action or title
        self.setProperty('workflowCard', tone)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay=QVBoxLayout(self); lay.setContentsMargins(14,12,14,12); lay.setSpacing(5)
        t=QLabel(title); t.setProperty('workflowTitle', True); lay.addWidget(t)
        v=QLabel(value); v.setProperty('workflowValue', True); lay.addWidget(v)
        d=QLabel(desc); d.setProperty('workflowDesc', True); d.setWordWrap(True); lay.addWidget(d)

    def mousePressEvent(self,event): self.clicked.emit(self.action)


class ChecklistWidget(QWidget):
    itemClicked = pyqtSignal(str)
    def __init__(self, items: list[tuple[str,bool,str]] | None = None, parent=None):
        super().__init__(parent); self.items=items or []; self.setMinimumHeight(280); self._rects=[]
    def set_items(self, items): self.items=items; self.update()
    def mousePressEvent(self,event):
        for rect,name in self._rects:
            if rect.contains(event.position()): self.itemClicked.emit(name); break
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); self._rects=[]
        if not self.items:
            p.setPen(QColor('#94a3b8')); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, '暂无检查项'); return
        y=8
        for name,ok,detail in self.items:
            rect=QRectF(8,y,self.width()-16,50); self._rects.append((rect,name))
            p.setBrush(QColor('#dcfce7') if ok else QColor('#fee2e2')); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(rect,10,10)
            p.setPen(QColor('#047857') if ok else QColor('#b91c1c')); f=QFont(); f.setBold(True); f.setPointSize(10); p.setFont(f)
            p.drawText(QRectF(18,y+7,48,16), Qt.AlignmentFlag.AlignLeft, '通过' if ok else '阻断')
            p.setPen(QColor('#0f172a')); p.drawText(QRectF(72,y+7,self.width()-92,16), Qt.AlignmentFlag.AlignLeft, name)
            p.setPen(QColor('#64748b')); p.setFont(QFont('Microsoft YaHei',8)); p.drawText(QRectF(72,y+25,self.width()-92,20), int(Qt.AlignmentFlag.AlignLeft.value | Qt.TextFlag.TextWordWrap.value), detail)
            y += 56
