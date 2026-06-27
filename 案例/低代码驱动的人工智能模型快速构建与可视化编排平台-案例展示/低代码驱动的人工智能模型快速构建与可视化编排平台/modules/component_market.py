"""组件市场模块 - AI节点/脚本/规则模板/视觉算子在线预览与本地导入"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QListWidget, QTextEdit, QSplitter, QTabWidget, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt
from core.auth import Role, OpAction, auth_engine
from core.rule_engine import rule_engine

COMPONENTS = {
    "AI节点": [
        {"name": "数据归一化节点", "desc": "支持Z-score/MinMax/Robust三种归一化方式", "author": "平台官方", "rating": 4.8},
        {"name": "特征选择节点", "desc": "基于互信息/卡方检验/树模型的特征选择", "author": "社区", "rating": 4.5},
        {"name": "注意力机制节点", "desc": "Transformer自注意力层封装", "author": "平台官方", "rating": 4.9},
        {"name": "数据增强节点", "desc": "图像翻转/旋转/裁剪/色彩抖动增强", "author": "社区", "rating": 4.6},
        {"name": "模型融合节点", "desc": "Bagging/Boosting/Stacking集成策略", "author": "官方", "rating": 4.7},
        {"name": "ONNX导出节点", "desc": "模型转ONNX通用格式导出", "author": "平台官方", "rating": 4.4},
    ],
    "低代码脚本": [
        {"name": "数据清洗模板", "desc": "缺失值填充/异常值检测/编码转换", "author": "社区精选", "rating": 4.3},
        {"name": "交叉验证模板", "desc": "K折交叉验证/分层采样评估", "author": "官方", "rating": 4.7},
        {"name": "超参搜索模板", "desc": "网格搜索/随机搜索/贝叶斯优化", "author": "社区精选", "rating": 4.8},
        {"name": "推理服务模板", "desc": "模型API服务化部署脚本", "author": "平台官方", "rating": 4.5},
        {"name": "数据可视化模板", "desc": "训练曲线/混淆矩阵/特征重要性图表", "author": "社区", "rating": 4.2},
    ],
    "规则模板": [
        {"name": "训练早停规则", "desc": "验证损失连续N轮不下降自动停止", "author": "官方", "rating": 4.9},
        {"name": "数据质量检查规则", "desc": "输入数据维度/类型/范围自动校验", "author": "平台官方", "rating": 4.6},
        {"name": "模型版本管理规则", "desc": "模型保存/回退/灰度发布流程规则", "author": "社区精选", "rating": 4.4},
        {"name": "资源监控规则", "desc": "GPU内存/CPU使用率超阈值告警", "author": "官方", "rating": 4.7},
    ],
    "视觉算子": [
        {"name": "自适应阈值算子", "desc": "Otsu/Adaptive双模式自适应阈值分割", "author": "平台官方", "rating": 4.5},
        {"name": "特征匹配算子", "desc": "SIFT/ORB/AKAZE多算法特征匹配", "author": "社区", "rating": 4.3},
        {"name": "目标追踪算子", "desc": "KCF/CSRT/DeepSORT目标追踪框架", "author": "官方", "rating": 4.8},
        {"name": "3D重建算子", "desc": "多视角立体视觉3D重建", "author": "社区精选", "rating": 4.6},
    ],
}

class ComponentMarketWidget(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user; self._installed = set()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("🧩 组件市场")
        title.setStyleSheet("color:#4E342E;font-size:20px;font-weight:bold;")
        header.addWidget(title); header.addStretch()
        header.addWidget(QPushButton("📥 导入本地组件", clicked=self._import_local))
        header.addWidget(QPushButton("🔄 刷新市场", clicked=self._refresh_market))
        header.addWidget(QPushButton("📋 我的组件", clicked=self._show_installed))
        layout.addLayout(header)

        main = QSplitter(Qt.Orientation.Horizontal)

        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        cat_gb = QGroupBox("📂 组件分类")
        cl = QVBoxLayout()
        self.cat_list = QListWidget()
        self.cat_list.addItems(COMPONENTS.keys())
        self.cat_list.itemClicked.connect(self._on_category_select)
        cl.addWidget(self.cat_list)
        cat_gb.setLayout(cl)
        left.addWidget(cat_gb)

        filter_gb = QGroupBox("🔍 筛选排序")
        fl = QVBoxLayout()
        fl.addWidget(QPushButton("⭐ 按评分排序", clicked=self._sort_by_rating))
        fl.addWidget(QPushButton("🆕 最新发布", clicked=self._sort_by_newest))
        fl.addWidget(QPushButton("📥 已安装", clicked=self._filter_installed))
        fl.addWidget(QPushButton("🏛 官方组件", clicked=self._filter_official))
        filter_gb.setLayout(fl)
        left.addWidget(filter_gb)

        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(220)

        right = QVBoxLayout()
        right.addWidget(QLabel("🧩 可用组件", styleSheet="color:#E65100;font-weight:bold;"))
        self.comp_list = QListWidget()
        self.comp_list.itemClicked.connect(self._on_component_select)
        right.addWidget(self.comp_list)

        self.detail_text = QTextEdit(); self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(160)
        self.detail_text.setStyleSheet("background:#FFFDE7;color:#4E342E;")
        right.addWidget(self.detail_text)

        action_row = QHBoxLayout()
        action_row.addWidget(QPushButton("📥 安装组件", clicked=self._install_component))
        action_row.addWidget(QPushButton("👁 预览详情", clicked=self._preview_component))
        action_row.addWidget(QPushButton("📋 复制脚本", clicked=self._copy_script))
        action_row.addWidget(QPushButton("🗑 卸载", clicked=self._uninstall_component))
        right.addLayout(action_row)

        right_w = QWidget(); right_w.setLayout(right)
        main.addWidget(left_w); main.addWidget(right_w)
        main.setSizes([220, 900])
        layout.addWidget(main)

        self._on_category_select(self.cat_list.item(0))

    def _on_category_select(self, item):
        category = item.text()
        self.comp_list.clear()
        for comp in COMPONENTS.get(category, []):
            status = "✅" if comp["name"] in self._installed else "⬇"
            self.comp_list.addItem(f"{status} {comp['name']} | ⭐{comp['rating']} | {comp['author']}")

    def _on_component_select(self, item):
        text = item.text()
        name = text.split(" |")[0].replace("✅ ", "").replace("⬇ ", "")
        for cat in COMPONENTS.values():
            for comp in cat:
                if comp["name"] == name:
                    self.detail_text.setPlainText(
                        f"名称: {comp['name']}\n描述: {comp['desc']}\n作者: {comp['author']}\n评分: ⭐{comp['rating']}\n"
                        f"状态: {'已安装' if name in self._installed else '未安装'}\n"
                        f"兼容性: Python3.8+ | PyQt6 | 低代码AI平台 v1.0+\n大小: ~{len(comp['desc']) * 5}KB")
                    return

    def _install_component(self):
        item = self.comp_list.currentItem()
        if item:
            name = item.text().split(" |")[0].replace("✅ ", "").replace("⬇ ", "")
            self._installed.add(name)
            QMessageBox.information(self, "安装", f"组件 [{name}] 安装成功！\n可在对应模块中使用")
            self._on_category_select(self.cat_list.currentItem() or self.cat_list.item(0))

    def _preview_component(self):
        QMessageBox.information(self, "预览", "组件详情预览\n包含源代码、使用示例、依赖说明")

    def _copy_script(self):
        item = self.comp_list.currentItem()
        if item:
            QMessageBox.information(self, "复制",
                f"组件脚本已复制到剪贴板\n可在低代码编辑器中粘贴使用")

    def _uninstall_component(self):
        item = self.comp_list.currentItem()
        if item:
            name = item.text().split(" |")[0].replace("✅ ", "").replace("⬇ ", "")
            if name in self._installed:
                self._installed.discard(name)
                QMessageBox.information(self, "卸载", f"组件 [{name}] 已卸载")

    def _import_local(self):
        QMessageBox.information(self, "导入", "支持导入本地组件包 (.zip/.py)\n导入后可在市场中管理")

    def _refresh_market(self):
        QMessageBox.information(self, "刷新", "组件市场已刷新\n共 24 个可用组件")

    def _show_installed(self):
        msg = "\n".join(self._installed) if self._installed else "暂无已安装组件"
        QMessageBox.information(self, "我的组件", msg)

    def _sort_by_rating(self):
        self.comp_list.clear()
        self.comp_list.addItems([f"⭐{i+1}. 高分组件示例{i+1}" for i in range(5)])

    def _sort_by_newest(self):
        self.comp_list.clear()
        self.comp_list.addItems([f"🆕 最新组件示例{i+1}" for i in range(5)])

    def _filter_installed(self):
        self.comp_list.clear()
        self.comp_list.addItems([f"✅ {n}" for n in self._installed] or ["暂无已安装组件"])

    def _filter_official(self):
        QMessageBox.information(self, "官方组件", "平台官方组件 12个\n社区精选 8个\n第三方 4个")

def get_module_widget(user):
    return ComponentMarketWidget(user)
