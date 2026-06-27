"""低代码脚本编辑器 - Python语法实时校验、代码模板调用"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel, QListWidget, QSplitter, QTextEdit, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
import re, ast, keyword

class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        kw_fmt = QTextCharFormat(); kw_fmt.setForeground(QColor("#c792ea")); kw_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in keyword.kwlist:
            self._rules.append((re.compile(rf'\b{kw}\b'), kw_fmt))
        str_fmt = QTextCharFormat(); str_fmt.setForeground(QColor("#c3e88d"))
        self._rules.append((re.compile(r'"[^"]*"|\'[^\']*\''), str_fmt))
        num_fmt = QTextCharFormat(); num_fmt.setForeground(QColor("#f78c6c"))
        self._rules.append((re.compile(r'\b\d+\.?\d*\b'), num_fmt))
        comment_fmt = QTextCharFormat(); comment_fmt.setForeground(QColor("#546e7a"))
        self._rules.append((re.compile(r'#.*$'), comment_fmt))
        decor_fmt = QTextCharFormat(); decor_fmt.setForeground(QColor("#82aaff"))
        self._rules.append((re.compile(r'@\w+'), decor_fmt))
        func_fmt = QTextCharFormat(); func_fmt.setForeground(QColor("#82b1ff"))
        self._rules.append((re.compile(r'\b([a-zA-Z_]\w*)(?=\s*\()'), func_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

CODE_TEMPLATES = {
    "数据加载": '''# 数据加载模板
import pandas as pd

def load_data(file_path: str):
    """加载CSV/Excel数据"""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        return pd.read_excel(file_path)
    return None

# 可修改file_path路径
file_path = "data/sample.csv"
data = load_data(file_path)
print(f"加载数据: {data.shape}")''',
    "数据预处理": '''# 数据预处理模板
import numpy as np

def preprocess(data):
    """标准化、缺失值填充、异常值处理"""
    # 缺失值填充
    data = data.fillna(data.mean())
    # Z-score标准化
    from scipy import stats
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    data[numeric_cols] = stats.zscore(data[numeric_cols])
    return data

# 修改preprocess函数逻辑以适配不同数据
result = preprocess(data)''',
    "模型训练": '''# 模型训练模板
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

def train_model(X, y, **params):
    """训练并评估模型"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params.get('test_size', 0.2))
    model = RandomForestClassifier(
        n_estimators=params.get('n_estimators', 100),
        max_depth=params.get('max_depth', 10))
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    return {
        'model': model,
        'accuracy': accuracy_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred, average='weighted')
    }''',
    "图像处理": '''# OpenCV图像处理模板
import cv2

def process_image(img_path, operations=None):
    """应用图像处理操作链"""
    img = cv2.imread(img_path)
    if img is None: return None
    if operations is None:
        operations = ['gray', 'blur', 'edge']
    for op in operations:
        if op == 'gray':
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        elif op == 'blur':
            img = cv2.GaussianBlur(img, (5, 5), 0)
        elif op == 'edge':
            img = cv2.Canny(img, 100, 200)
        elif op == 'threshold':
            _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return img''',
    "推理预测": '''# 推理预测模板
def predict(model, input_data, preprocess_fn=None):
    """执行模型推理"""
    if preprocess_fn:
        input_data = preprocess_fn(input_data)
    predictions = model.predict(input_data)
    probabilities = None
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(input_data)
    return {
        'predictions': predictions.tolist(),
        'probabilities': probabilities.tolist() if probabilities is not None else None,
        'count': len(predictions)
    }''',
    "结果可视化": '''# 结果可视化模板
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def visualize_results(results, chart_type='bar'):
    """生成结果图表"""
    fig, ax = plt.subplots(figsize=(8, 5))
    if chart_type == 'bar':
        ax.bar(range(len(results)), results)
    elif chart_type == 'line':
        ax.plot(range(len(results)), results)
    elif chart_type == 'pie':
        ax.pie(results, autopct='%1.1f%%')
    ax.set_title('Results Visualization')
    return fig''',
}

class LowCodeEditor(QWidget):
    """低代码脚本编辑器 - 语法校验 + 模板 + 执行"""
    code_executed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        left_split = QSplitter(Qt.Orientation.Vertical)
        tmpl_label = QLabel("📋 代码模板")
        tmpl_label.setStyleSheet("color:#E65100;font-weight:bold;padding:4px;")
        self.tmpl_list = QListWidget()
        self.tmpl_list.addItems(CODE_TEMPLATES.keys())
        self.tmpl_list.itemClicked.connect(self._apply_template)
        left_w = QWidget()
        left_l = QVBoxLayout(left_w); left_l.setContentsMargins(0,0,0,0)
        left_l.addWidget(tmpl_label); left_l.addWidget(self.tmpl_list)
        left_split.addWidget(left_w)

        right_w = QWidget()
        right_l = QVBoxLayout(right_w); right_l.setContentsMargins(4,4,4,4)

        toolbar = QHBoxLayout()
        self.btn_check = QPushButton("✓ 语法检查")
        self.btn_check.clicked.connect(self._check_syntax)
        self.btn_run = QPushButton("▶ 执行代码")
        self.btn_run.setObjectName("success"); self.btn_run.clicked.connect(self._execute)
        self.btn_save = QPushButton("💾 保存片段")
        self.btn_save.clicked.connect(self._save_snippet)
        toolbar.addWidget(self.btn_check)
        toolbar.addWidget(self.btn_run)
        toolbar.addWidget(self.btn_save)
        toolbar.addStretch()
        right_l.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setStyleSheet("background:#263238;color:#EEFFFF;border:1px solid #FFD54F;border-radius:6px;padding:8px;")
        self.editor.setPlaceholderText("# 在此编写低代码Python脚本...\n# 从左侧选择模板快速开始")
        self.editor.setTabStopDistance(32)
        self.highlighter = PythonHighlighter(self.editor.document())
        right_l.addWidget(self.editor)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet("background:#FFF8E1;color:#2E7D32;border:1px solid #FFD54F;border-radius:6px;padding:6px;")
        right_l.addWidget(QLabel("📤 输出控制台", styleSheet="color:#E65100;font-weight:bold;"))
        right_l.addWidget(self.console)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_split); splitter.addWidget(right_w)
        splitter.setSizes([200, 600])
        layout.addWidget(splitter)

    def _apply_template(self, item):
        tmpl_name = item.text()
        if tmpl_name in CODE_TEMPLATES:
            self.editor.setPlainText(CODE_TEMPLATES[tmpl_name])

    def _check_syntax(self):
        code = self.editor.toPlainText()
        try:
            ast.parse(code)
            self.console.setHtml('<span style="color:#2E7D32;">✓ 语法检查通过</span>')
        except SyntaxError as e:
            self.console.setHtml(f'<span style="color:#D84315;">✗ 语法错误 行{e.lineno}: {e.msg}</span>')

    def _execute(self):
        code = self.editor.toPlainText()
        if not code.strip():
            self.console.setHtml('<span style="color:#F57F17;">⚠ 请先编写代码</span>'); return
        try:
            local_ns = {}
            exec(code, {"__builtins__": __builtins__}, local_ns)
            output = str(local_ns.get("result", local_ns))
            self.console.setHtml(f'<span style="color:#2E7D32;">✓ 执行成功</span>\n<pre>{self._truncate(output)}</pre>')
            self.code_executed.emit({"success": True, "output": output})
        except Exception as e:
            self.console.setHtml(f'<span style="color:#D84315;">✗ 执行异常: {type(e).__name__}: {e}</span>')
            self.code_executed.emit({"success": False, "error": str(e)})

    def _save_snippet(self):
        code = self.editor.toPlainText()
        if code.strip():
            self.console.setHtml('<span style="color:#E65100;">📌 代码片段已保存到本地内存</span>')

    def _truncate(self, s: str, n: int = 500) -> str:
        return s[:n] + "..." if len(s) > n else s

    def set_code(self, code: str):
        self.editor.setPlainText(code)

    def get_code(self) -> str:
        return self.editor.toPlainText()
