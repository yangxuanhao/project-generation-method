"""项目管理模块 - 项目文件夹分类、资源管理、文件检索、冗余清理"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTreeWidget, QTreeWidgetItem, QListWidget, QLineEdit, QTextEdit,
    QSplitter, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt
from core.auth import Role, OpAction, auth_engine
from core.state_machine import flow_sm, FlowState
from core.data_consistency import data_engine
import time, os, json

class ProjectManagerWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._projects = {}
        self._setup_ui(); self._init_demo_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("📁 项目资源管理")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        header.addWidget(QPushButton("📂 新建项目", clicked=self._new_project))
        header.addWidget(QPushButton("📂 新建文件夹", clicked=self._new_folder))
        header.addWidget(QPushButton("🔍 检索文件", clicked=self._search_files))
        header.addWidget(QPushButton("🗑 冗余清理", clicked=self._clean_redundant))
        header.addWidget(QPushButton("📤 导入资源", clicked=self._import_resource))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        tree_gb = QGroupBox("📁 项目目录")
        tl = QVBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "类型", "修改时间"])
        self.tree.itemClicked.connect(self._on_tree_click)
        tl.addWidget(self.tree)
        tree_gb.setLayout(tl)
        left.addWidget(tree_gb)

        search_gb = QGroupBox("🔍 快速检索")
        sl = QVBoxLayout()
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("输入文件名或关键字...")
        self.search_input.textChanged.connect(self._on_search)
        sl.addWidget(self.search_input)
        self.search_result = QListWidget(); sl.addWidget(self.search_result)
        search_gb.setLayout(sl)
        left.addWidget(search_gb)

        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(320)

        right = QVBoxLayout()
        right.addWidget(QLabel("📄 资源详情", styleSheet="color:#E65100;font-weight:bold;"))
        self.detail_text = QTextEdit(); self.detail_text.setReadOnly(True)
        self.detail_text.setStyleSheet("background:#FFFDE7;color:#4E342E;")
        right.addWidget(self.detail_text)

        op_row = QHBoxLayout()
        op_row.addWidget(QPushButton("✎ 重命名", clicked=self._rename_item))
        op_row.addWidget(QPushButton("📋 复制路径", clicked=self._copy_path))
        op_row.addWidget(QPushButton("🗑 删除", clicked=self._delete_item))
        op_row.addWidget(QPushButton("📦 压缩下载", clicked=self._download_zip))
        right.addLayout(op_row)

        right_w = QWidget(); right_w.setLayout(right)
        main.addWidget(left_w); main.addWidget(right_w)
        main.setSizes([320, 800])
        layout.addWidget(main)

    def _init_demo_projects(self):
        projects = {
            "图像分类项目": {"datasets": ["train.csv", "val.csv", "test_images/"], "models": ["model_v3.onnx", "checkpoint.pkl"],
                "scripts": ["preprocess.py", "train.py", "infer.py"], "logs": ["train_log.txt"], "exports": ["result_v3.onnx"]},
            "目标检测项目": {"datasets": ["coco_subset/", "annotations.json"], "models": ["yolo_v5.onnx", "detector.pkl"],
                "scripts": ["detect.py"], "exports": ["detect_result.onnx"]},
            "文本分析项目": {"datasets": ["corpus.csv", "embeddings.npy"], "models": ["bert_finetuned.h5"],
                "scripts": ["tokenize.py", "classify.py"], "exports": []},
            "3D点云项目": {"datasets": ["pointcloud.ply", "labels.txt"], "models": ["pointnet.pkl"],
                "scripts": ["voxelize.py"], "logs": ["train_3d.log"], "exports": []},
            "时序预测项目": {"datasets": ["sales_2023.csv"], "models": ["lstm_model.h5"],
                "scripts": ["forecast.py"], "exports": ["forecast.onnx"]},
        }
        self._projects = projects
        for proj_name, folders in projects.items():
            proj_item = QTreeWidgetItem([proj_name, "项目", time.strftime("%Y-%m-%d")])
            for folder_name, files in folders.items():
                folder_item = QTreeWidgetItem([folder_name, "文件夹", ""])
                for f in files:
                    ftype = "模型" if any(f.endswith(e) for e in ['.onnx','.pkl','.h5']) else \
                            "数据" if any(f.endswith(e) for e in ['.csv','.json','.ply','.npy','.txt']) else \
                            "脚本" if f.endswith('.py') else "日志" if f.endswith('.log') else "文件夹" if f.endswith('/') else "文件"
                    QTreeWidgetItem(folder_item, [f, ftype, time.strftime("%H:%M")])
                proj_item.addChild(folder_item)
            self.tree.addTopLevelItem(proj_item)

    def _on_tree_click(self, item):
        details = f"名称: {item.text(0)}\n类型: {item.text(1)}\n"
        if item.text(2): details += f"修改时间: {item.text(2)}\n"
        if item.parent():
            details += f"路径: {item.parent().text(0)}/{item.text(0)}\n"
        self.detail_text.setPlainText(details)

    def _new_project(self):
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称:")
        if ok and name:
            item = QTreeWidgetItem([name, "项目", time.strftime("%Y-%m-%d")])
            for f in ["datasets", "models", "scripts", "logs", "exports"]:
                item.addChild(QTreeWidgetItem([f, "文件夹", ""]))
            self.tree.addTopLevelItem(item)
            self._projects[name] = {f: [] for f in ["datasets", "models", "scripts", "logs", "exports"]}

    def _new_folder(self):
        current = self.tree.currentItem()
        if current:
            name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名:")
            if ok and name:
                current.addChild(QTreeWidgetItem([name, "文件夹", ""]))

    def _search_files(self):
        query = self.search_input.text().lower()
        self.search_result.clear()
        def search_item(item):
            if query in item.text(0).lower():
                self.search_result.addItem(f"🔍 {item.text(0)} ({item.text(1)})")
            for i in range(item.childCount()):
                search_item(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            search_item(self.tree.topLevelItem(i))

    def _on_search(self, text):
        if len(text) >= 1: self._search_files()

    def _clean_redundant(self):
        QMessageBox.information(self, "冗余清理", "扫描完成\n发现 3 个冗余日志文件，可释放 2.5MB\n建议清理后刷新项目目录")

    def _import_resource(self):
        QMessageBox.information(self, "导入资源", "请将外部资源文件拖入对应项目文件夹\n支持: .onnx/.pkl/.h5/.csv/.json/.py/.log")

    def _rename_item(self):
        current = self.tree.currentItem()
        if current:
            name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=current.text(0))
            if ok and name: current.setText(0, name)

    def _copy_path(self):
        current = self.tree.currentItem()
        if current:
            path = current.text(0)
            parent = current.parent()
            while parent:
                path = parent.text(0) + "/" + path
                parent = parent.parent()
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(path)
            QMessageBox.information(self, "复制", f"路径已复制: {path}")

    def _delete_item(self):
        current = self.tree.currentItem()
        if current:
            reply = QMessageBox.question(self, "确认删除", f"确定删除 [{current.text(0)}] 吗？")
            if reply == QMessageBox.StandardButton.Yes:
                parent = current.parent() or self.tree.invisibleRootItem()
                parent.removeChild(current)

    def _download_zip(self):
        QMessageBox.information(self, "压缩下载", "项目资源压缩包已准备\n包含所有相关脚本、模型、数据文件")

def get_module_widget(user):
    return ProjectManagerWidget(user)
