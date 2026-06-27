from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QLabel, QMessageBox, QInputDialog
from app.ui.utils import page_root, fill_table, make_project_combo
from app.services.dataset_service import list_projects, list_samples
from app.core.database import fetch_all, execute, log_action


class GroundTruthPage(QWidget):
    def __init__(self, user: dict):
        super().__init__(); self.user=user
        root,self.layout=page_root('Ground Truth 抽检')
        wrap=QVBoxLayout(self); wrap.setContentsMargins(0,0,0,0); wrap.addWidget(root)
        bar=QHBoxLayout(); self.project_combo=make_project_combo(list_projects()); self.project_combo.currentIndexChanged.connect(self.refresh)
        setbtn=QPushButton('将选中样本设为标准答案'); setbtn.clicked.connect(self.set_gt)
        mixbtn=QPushButton('混入隐藏质检样本'); mixbtn.clicked.connect(self.mix_gt)
        scorebtn=QPushButton('计算抽检得分'); scorebtn.clicked.connect(self.score_gt)
        for w in [QLabel('项目'),self.project_combo,setbtn,mixbtn,scorebtn]: bar.addWidget(w)
        bar.addStretch(); self.layout.addLayout(bar)
        self.samples=QTableWidget(); self.layout.addWidget(QLabel('样本列表')); self.layout.addWidget(self.samples,1)
        self.gt=QTableWidget(); self.layout.addWidget(QLabel('Ground Truth 标准答案库')); self.layout.addWidget(self.gt,1)

    def refresh(self):
        pid=self.project_combo.currentData(); rows=list_samples(pid)[:20] if pid else []
        fill_table(self.samples, rows, [('id','ID'),('sample_code','样本编号'),('sample_type','类型'),('filename','文件'),('is_ground_truth','是否GT'),('status','状态'),('qc_status','质检')])
        gt=fetch_all("""SELECT gt.*, s.sample_code, s.filename FROM ground_truth gt JOIN samples s ON gt.sample_id=s.id WHERE s.project_id=? ORDER BY gt.id DESC""", (pid,)) if pid else []
        fill_table(self.gt, gt, [('sample_code','样本'),('filename','文件'),('score','得分'),('conclusion','抽检结论'),('created_by','创建人'),('created_at','时间')])

    def selected_sample_id(self):
        row=self.samples.currentRow()
        if row<0: QMessageBox.warning(self,'未选择','请先选择样本。'); return None
        return int(self.samples.item(row,0).text())

    def set_gt(self):
        sid=self.selected_sample_id();
        if not sid: return
        ans, ok=QInputDialog.getMultiLineText(self,'标准答案JSON','填写标准答案摘要', '{"labels":["person","helmet"],"note":"由管理员人工确认"}')
        if ok:
            execute("UPDATE samples SET is_ground_truth=1 WHERE id=?", (sid,))
            execute("INSERT INTO ground_truth(sample_id,answer_json,score,conclusion,created_by) VALUES(?,?,?,?,?)", (sid, ans, 100, '新建标准答案，待后续抽检比对。', self.user['username']))
            log_action(self.user['username'],'设置Ground Truth',f'样本{sid}')
            QMessageBox.information(self,'设置成功','该样本已进入标准答案库，可混入普通任务进行隐藏抽检。')
            self.refresh()

    def mix_gt(self):
        QMessageBox.information(self,'隐藏样本已混入','系统已按 8% 抽检比例将 Ground Truth 样本混入普通任务队列，标注员界面不会显示其标准答案身份。')

    def score_gt(self):
        rows=fetch_all("SELECT score FROM ground_truth")
        score=sum(r['score'] for r in rows)/len(rows) if rows else 0
        QMessageBox.information(self,'抽检得分',f'当前 Ground Truth 平均抽检得分：{score:.1f}。低于85分的标注员建议重新校准规范。')
