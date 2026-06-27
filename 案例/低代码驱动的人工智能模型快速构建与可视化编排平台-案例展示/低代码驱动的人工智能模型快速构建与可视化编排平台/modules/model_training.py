"""模型训练模块 - 超参配置、训练启停、断点续训、模型导入导出"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QProgressBar,
    QSlider, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QTimer
from core.auth import Role, OpAction, auth_engine
from core.state_machine import FlowState, flow_sm, task_sm, TaskState
from core.rule_engine import rule_engine, TriggerType, Condition, CompareOp, RuleAction
from core.data_consistency import data_engine
from core.algorithms import ParameterOptimizer
import random, time

class ModelTrainingWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._training = False
        self._progress = 0; self._epoch = 0; self._total_epochs = 50
        self._timer = QTimer(self); self._timer.timeout.connect(self._training_step)
        self._setup_ui(); self._init_demo()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()

        tmpl_gb = QGroupBox("🎯 模型模板")
        tl = QVBoxLayout()
        self.tmpl_combo = QComboBox()
        self.tmpl_combo.addItems(["分类模型-RandomForest", "分类模型-SVM", "回归模型-XGBoost",
            "目标检测-YOLO", "图像分割-U-Net", "时序预测-LSTM", "文本分析-BERT"])
        tl.addWidget(QLabel("选择模板:")); tl.addWidget(self.tmpl_combo)
        tmpl_gb.setLayout(tl)
        left_panel.addWidget(tmpl_gb)

        param_gb = QGroupBox("⚙ 超参数配置")
        pg = QGridLayout()
        params = [("学习率", 0.001, 0.00001, 0.1, 0.0001), ("批次大小", 32, 1, 256, 1),
                  ("训练轮次", 50, 1, 500, 1), ("早停轮次", 10, 1, 100, 1),
                  ("Dropout率", 0.2, 0.0, 0.9, 0.05), ("L2正则化", 0.001, 0.0, 0.1, 0.001)]
        self._param_spinners = {}
        for r, (name, default, min_v, max_v, step) in enumerate(params):
            pg.addWidget(QLabel(name), r, 0)
            if isinstance(default, int):
                sp = QSpinBox(); sp.setRange(int(min_v), int(max_v)); sp.setValue(default)
            else:
                sp = QDoubleSpinBox(); sp.setRange(min_v, max_v); sp.setSingleStep(step); sp.setValue(default)
            self._param_spinners[name] = sp; pg.addWidget(sp, r, 1)
        param_gb.setLayout(pg)
        left_panel.addWidget(param_gb)

        ctrl_gb = QGroupBox("🎮 训练控制")
        cl = QVBoxLayout()
        self.btn_start = QPushButton("▶ 开始训练"); self.btn_start.setObjectName("success")
        self.btn_start.clicked.connect(self._start_training)
        self.btn_pause = QPushButton("⏸ 暂停训练"); self.btn_pause.setObjectName("warning")
        self.btn_pause.clicked.connect(self._pause_training)
        self.btn_stop = QPushButton("⏹ 停止训练"); self.btn_stop.setObjectName("danger")
        self.btn_stop.clicked.connect(self._stop_training)
        self.btn_resume = QPushButton("↩ 断点续训"); self.btn_resume.clicked.connect(self._resume_training)
        cl.addWidget(self.btn_start); cl.addWidget(self.btn_pause)
        cl.addWidget(self.btn_stop); cl.addWidget(self.btn_resume)
        ctrl_gb.setLayout(cl)
        left_panel.addWidget(ctrl_gb)

        export_gb = QGroupBox("💾 模型导出/导入")
        el = QVBoxLayout()
        el.addWidget(QPushButton("📤 导出模型(ONNX/PKL)", clicked=self._export_model))
        el.addWidget(QPushButton("📥 导入外部模型", clicked=self._import_model))
        el.addWidget(QPushButton("📋 导出训练日志", clicked=self._export_log))
        export_gb.setLayout(el)
        left_panel.addWidget(export_gb)

        left_widget = QWidget(); left_widget.setLayout(left_panel); left_widget.setMaximumWidth(280)

        right_panel = QVBoxLayout()

        progress_gb = QGroupBox("📊 训练进度")
        pl = QVBoxLayout()
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        pl.addWidget(self.progress_bar)
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setStyleSheet("color:#2E7D32;font-weight:bold;font-size:14px;")
        pl.addWidget(self.status_label)
        info_row = QHBoxLayout()
        self.epoch_label = QLabel("Epoch: 0/50"); self.loss_label = QLabel("Loss: --")
        self.acc_label = QLabel("Accuracy: --"); self.time_label = QLabel("耗时: --")
        for lbl in [self.epoch_label, self.loss_label, self.acc_label, self.time_label]:
            lbl.setStyleSheet("color:#795548;background:#FFFFFF;border-radius:4px;padding:6px;")
            info_row.addWidget(lbl)
        pl.addLayout(info_row)
        progress_gb.setLayout(pl)
        right_panel.addWidget(progress_gb)

        log_gb = QGroupBox("📜 训练日志")
        ll = QVBoxLayout()
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background:#FFF8E1;color:#2E7D32;font-family:Consolas;font-size:11px;")
        ll.addWidget(self.log_text)
        log_gb.setLayout(ll)
        right_panel.addWidget(log_gb)

        metrics_gb = QGroupBox("📈 训练指标监控（支持滚轮浏览）")
        ml = QVBoxLayout()
        self.metrics_table = QTableWidget(0, 5)
        self.metrics_table.setHorizontalHeaderLabels(["Epoch", "Train Loss", "Val Loss", "Accuracy", "F1 Score"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ml.addWidget(self.metrics_table)
        metrics_gb.setLayout(ml)
        right_panel.addWidget(metrics_gb)

        right_widget = QWidget(); right_widget.setLayout(right_panel)

        layout.addWidget(left_widget); layout.addWidget(right_widget, 1)

    def _init_demo(self):
        for epoch in range(1, 6):
            self.metrics_table.insertRow(self.metrics_table.rowCount())
            for col, val in enumerate([epoch, round(1.5/epoch+random.uniform(0,0.1),4),
                round(1.8/epoch+random.uniform(0,0.1),4), round(0.5+0.08*epoch,4), round(0.45+0.07*epoch,4)]):
                self.metrics_table.setItem(self.metrics_table.rowCount()-1, col, QTableWidgetItem(str(val)))

    def _start_training(self):
        if not auth_engine.check_permission(self.user, "model_training", OpAction.EXECUTE):
            QMessageBox.warning(self, "权限不足", "当前角色无权执行训练"); return
        self._training = True; self._progress = 0; self._epoch = 0
        self._total_epochs = self._param_spinners["训练轮次"].value()
        self._timer.start(150)
        self.status_label.setText("状态: 训练中..."); self.status_label.setStyleSheet("color:#F57F17;font-weight:bold;font-size:14px;")
        self._log("=" * 40); self._log(f"开始训练 - 模板: {self.tmpl_combo.currentText()}")
        self._log(f"学习率: {self._param_spinners['学习率'].value()}, 批次: {self._param_spinners['批次大小'].value()}")
        task_sm.create_task("train_001", "模型训练", priority=8)
        task_sm.transition("train_001", TaskState.EXECUTING)

    def _pause_training(self):
        if self._training:
            self._timer.stop(); self._training = False
            self.status_label.setText("状态: 已暂停"); self.status_label.setStyleSheet("color:#F57F17;font-weight:bold;")
            self._log("⏸ 训练已暂停"); task_sm.transition("train_001", TaskState.PAUSED)

    def _stop_training(self):
        self._timer.stop(); self._training = False
        self.status_label.setText("状态: 已停止"); self.status_label.setStyleSheet("color:#D84315;font-weight:bold;")
        self._log("⏹ 训练已停止"); task_sm.transition("train_001", TaskState.CANCELLED)

    def _resume_training(self):
        if not self._training:
            self._training = True; self._timer.start(150)
            self.status_label.setText("状态: 续训中..."); self.status_label.setStyleSheet("color:#F57F17;font-weight:bold;")
            self._log("↩ 断点续训 - 恢复检查点")

    def _training_step(self):
        self._progress += 1
        if self._progress % 5 == 0:
            self._epoch = min(self._total_epochs, self._progress // 5)
            self.progress_bar.setValue(int(self._epoch / self._total_epochs * 100))
            loss = round(2.0 / (self._epoch + 1) + random.uniform(-0.05, 0.05), 4)
            acc = round(min(0.98, 0.5 + 0.01 * self._epoch + random.uniform(-0.02, 0.02)), 4)
            f1 = round(acc - random.uniform(0.01, 0.05), 4)
            self.epoch_label.setText(f"Epoch: {self._epoch}/{self._total_epochs}")
            self.loss_label.setText(f"Loss: {loss}"); self.acc_label.setText(f"Accuracy: {acc}")
            row = self.metrics_table.rowCount()
            self.metrics_table.insertRow(row)
            for col, val in enumerate([self._epoch, loss, round(loss+0.1,4), acc, f1]):
                self.metrics_table.setItem(row, col, QTableWidgetItem(str(val)))
            self._log(f"Epoch {self._epoch}/{self._total_epochs} | Loss: {loss} | Acc: {acc} | F1: {f1}")
        if self._epoch >= self._total_epochs:
            self._timer.stop(); self._training = False
            self.status_label.setText("状态: 训练完成 ✓"); self.status_label.setStyleSheet("color:#2E7D32;font-weight:bold;font-size:14px;")
            self._log("✅ 训练完成!"); task_sm.transition("train_001", TaskState.COMPLETED)

    def _log(self, msg: str):
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def _export_model(self):
        QMessageBox.information(self, "导出", f"模型已导出为 ONNX/PKL 格式\n保存路径: ./exports/{self.tmpl_combo.currentText()}_{int(time.time())}.onnx")

    def _import_model(self):
        QMessageBox.information(self, "导入", "请选择模型文件 (.onnx/.pkl/.h5)\n导入后可在推理节点中使用")

    def _export_log(self):
        QMessageBox.information(self, "导出日志", f"训练日志已导出\n共 {self.metrics_table.rowCount()} 条记录")

def get_module_widget(user):
    return ModelTrainingWidget(user)
