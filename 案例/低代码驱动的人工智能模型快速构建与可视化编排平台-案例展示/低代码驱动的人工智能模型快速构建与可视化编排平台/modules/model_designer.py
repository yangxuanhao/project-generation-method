"""模型设计器 - 可视化画布编排AI流程、节点管理、流程版本管理"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QGroupBox, QSplitter, QComboBox, QTextEdit, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core.auth import Role, OpAction, auth_engine
from core.state_machine import FlowState, flow_sm
from core.rule_engine import rule_engine, TriggerType, Condition, CompareOp, RuleAction, LogicOp
from core.data_consistency import data_engine
from ui.canvas import ModelCanvas
import json, time

NODE_TYPES = ["数据预处理", "传统机器学习", "深度学习", "推理", "分支判断", "循环", "数据输出"]
FLOW_STATES = [s.value for s in FlowState]

class ModelDesignerWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self.current_flow_id = None
        self._setup_ui()
        self._init_demo()
        self._check_perm()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        flow_gb = QGroupBox("📋 流程管理")
        fl = QVBoxLayout()
        self.flow_combo = QComboBox()
        self.flow_combo.addItems(["图像分类流程", "目标检测流程", "文本分析流程", "3D点云流程", "时序预测流程"])
        self.flow_combo.currentTextChanged.connect(self._on_flow_change)
        fl.addWidget(QLabel("当前流程:")); fl.addWidget(self.flow_combo)

        state_row = QHBoxLayout()
        self.state_label = QLabel("编辑态")
        self.state_label.setStyleSheet("color:#E65100;font-weight:bold;font-size:14px;background:#FFFFFF;border:1px solid #FFD54F;border-radius:6px;padding:6px 12px;")
        state_row.addWidget(QLabel("状态:")); state_row.addWidget(self.state_label); state_row.addStretch()
        fl.addLayout(state_row)

        st_btns = QHBoxLayout()
        for state, btn_style in [("调试态", "warning"), ("运行态", "success"), ("暂停态", ""), ("编辑态", "danger")]:
            btn = QPushButton(state)
            if btn_style: btn.setObjectName(btn_style)
            btn.clicked.connect(lambda checked, s=state: self._change_state(s))
            st_btns.addWidget(btn)
        fl.addLayout(st_btns)
        fl.addWidget(QLabel("版本管理:"))
        self.version_combo = QComboBox(); self.version_combo.addItems(["v1.0 (当前)", "v0.9", "v0.8"])
        fl.addWidget(self.version_combo)
        ver_row = QHBoxLayout()
        ver_row.addWidget(QPushButton("💾 保存版本", clicked=self._save_version))
        ver_row.addWidget(QPushButton("↩ 版本回退", clicked=self._rollback_version))
        fl.addLayout(ver_row)
        flow_gb.setLayout(fl)
        left_panel.addWidget(flow_gb)

        node_gb = QGroupBox("🧩 节点类型")
        nl = QVBoxLayout()
        self.node_list = QListWidget()
        self.node_list.addItems(NODE_TYPES)
        self.node_list.itemClicked.connect(self._add_node_from_list)
        nl.addWidget(self.node_list)
        node_gb.setLayout(nl)
        left_panel.addWidget(node_gb)

        action_gb = QGroupBox("⚡ 操作")
        al = QVBoxLayout()
        actions = [("🔗 连线选中节点", self._connect_nodes), ("📐 自动布局", self._auto_layout),
                   ("📏 水平对齐", lambda: self._align("hcenter")), ("📏 垂直对齐", lambda: self._align("vcenter")),
                   ("🔲 网格排列", lambda: self._align("grid")), ("↩ 撤销", self._undo),
                   ("↪ 重做", self._redo), ("🗑 清空画布", self._clear)]
        for label, handler in actions:
            btn = QPushButton(label); btn.clicked.connect(handler); al.addWidget(btn)
        action_gb.setLayout(al)
        left_panel.addWidget(action_gb)

        left_widget = QWidget(); left_widget.setLayout(left_panel); left_widget.setMaximumWidth(260)

        right_panel = QVBoxLayout()
        self.canvas = ModelCanvas()
        self.canvas.flow_changed.connect(self._on_flow_modified)
        self.canvas.status_message.connect(self._on_status_msg)
        right_panel.addWidget(self.canvas)

        info_bar = QHBoxLayout()
        self.info_label = QLabel("节点:0 | 连线:0 | 就绪")
        self.info_label.setStyleSheet("color:#795548;padding:4px;font-size:12px;")
        info_bar.addWidget(self.info_label); info_bar.addStretch()
        right_panel.addLayout(info_bar)

        right_widget = QWidget(); right_widget.setLayout(right_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget); splitter.addWidget(right_widget)
        splitter.setSizes([260, 1100])
        layout.addWidget(splitter)

    def _init_demo(self):
        self._flow_cache = {}
        flow_configs = {
            "图像分类流程": [
                ("数据预处理", "数据加载", 50, 50), ("数据预处理", "图像缩放", 50, 180),
                ("数据预处理", "灰度化处理", 50, 310), ("传统机器学习", "特征提取", 280, 120),
                ("深度学习", "CNN推理", 280, 250), ("数据输出", "结果输出", 520, 180),
            ],
            "目标检测流程": [
                ("数据预处理", "视频帧提取", 50, 80), ("深度学习", "YOLO检测", 280, 120),
                ("推理", "NMS后处理", 280, 250), ("数据输出", "标注输出", 520, 160),
            ],
            "文本分析流程": [
                ("数据预处理", "文本分词", 50, 100), ("数据预处理", "词向量化", 50, 220),
                ("深度学习", "BERT编码", 300, 160), ("推理", "情感分类", 520, 160),
            ],
            "3D点云流程": [
                ("数据预处理", "点云采样", 50, 80), ("数据预处理", "体素化", 50, 200),
                ("深度学习", "PointNet", 300, 140), ("数据输出", "分割结果", 520, 160),
            ],
            "时序预测流程": [
                ("数据预处理", "序列窗口化", 50, 100), ("深度学习", "LSTM层", 280, 100),
                ("深度学习", "注意力层", 280, 220), ("数据输出", "预测输出", 520, 160),
            ],
        }
        self._flow_configs = flow_configs
        self.current_flow_id = "flow_图像分类流程"
        flow_sm.create_flow(self.current_flow_id, {"name": "图像分类流程"})
        for ntype, label, x, y in flow_configs.get("图像分类流程", []):
            self.canvas.add_node(ntype, label, x, y)
        self._update_info()

    def _add_node_from_list(self, item):
        node_type = item.text()
        label, ok = QInputDialog.getText(self, "新建节点", "节点标签:", text=f"{node_type}节点")
        if ok and label:
            self.canvas.add_node(node_type, label)
            self._update_info()

    def _connect_nodes(self, _checked=None): self.canvas.connect_nodes(); self._update_info()
    def _auto_layout(self, _checked=None): self.canvas.auto_layout(); self._update_info()
    def _align(self, mode): self.canvas.align_nodes(mode)
    def _undo(self, _checked=None): self.canvas.undo(); self._update_info()
    def _redo(self, _checked=None): self.canvas.redo(); self._update_info()

    def _clear(self):
        reply = QMessageBox.question(self, "确认", "确定清空画布吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas.clear_all(); self._update_info()

    def _change_state(self, target_str: str):
        if not self.current_flow_id: return
        target_map = {"编辑态": FlowState.EDITING, "调试态": FlowState.DEBUGGING,
                      "运行态": FlowState.RUNNING, "暂停态": FlowState.PAUSED}
        target = target_map.get(target_str)
        if target and flow_sm.transition(self.current_flow_id, target, self.user.username):
            self.state_label.setText(target_str)
            if target == FlowState.RUNNING:
                self._evaluate_rules()
            QMessageBox.information(self, "状态变更", f"流程已切换至 [{target_str}]")
        else:
            QMessageBox.warning(self, "操作失败", f"无法从当前状态切换至 [{target_str}]，请检查状态流转规则")

    def _evaluate_rules(self):
        flow_data = self.canvas.get_flow_data()
        context = {"flow_id": self.current_flow_id, "node_count": len(flow_data["nodes"]),
                   "edge_count": len(flow_data["edges"]), "user": self.user.username}
        fired = rule_engine.evaluate_all(context, TriggerType.NODE)
        if fired:
            msgs = "\n".join([f"• {r.name} (优先级:{r.priority})" for r in fired])
            QMessageBox.information(self, "规则触发", f"以下业务规则已触发:\n{msgs}")

    def _save_version(self):
        ver_name = f"v{int(time.time()) % 1000}"
        self.version_combo.addItem(ver_name)
        self.version_combo.setCurrentText(ver_name)
        flow_data = self.canvas.get_flow_data()
        data_engine.register_node(self.current_flow_id, "snapshot", flow_data)
        QMessageBox.information(self, "保存", f"版本 [{ver_name}] 已保存")

    def _rollback_version(self):
        flow_sm.rollback(self.current_flow_id)
        QMessageBox.information(self, "回退", "已回退至上个版本状态")

    def _on_flow_change(self, name: str):
        if self.current_flow_id:
            self._flow_cache[self.current_flow_id] = self.canvas.get_flow_data()
        self.current_flow_id = f"flow_{name.replace(' ','_')}"
        flow_sm.create_flow(self.current_flow_id, {"name": name})
        if self.current_flow_id in self._flow_cache:
            self.canvas.load_flow_data(self._flow_cache[self.current_flow_id])
        elif name in self._flow_configs:
            self.canvas.clear_all()
            for ntype, label, x, y in self._flow_configs[name]:
                self.canvas.add_node(ntype, label, x, y)
        else:
            self.canvas.clear_all()
        self._update_info()

    def _on_flow_modified(self):
        self._update_info()

    def _on_status_msg(self, msg: str):
        self.info_label.setText(msg)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(4000, self._update_info)

    def _update_info(self):
        flow_data = self.canvas.get_flow_data()
        self.info_label.setText(f"节点:{len(flow_data['nodes'])} | 连线:{len(flow_data['edges'])} | 流程:{self.current_flow_id}")

    def _check_perm(self):
        if not auth_engine.check_permission(self.user, "model_designer", OpAction.EDIT):
            QMessageBox.warning(self, "权限提示", "当前角色仅可查看，编辑功能受限")

def get_module_widget(user):
    return ModelDesignerWidget(user)
