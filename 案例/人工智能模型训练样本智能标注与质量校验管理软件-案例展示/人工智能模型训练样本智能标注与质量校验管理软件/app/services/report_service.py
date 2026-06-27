from datetime import datetime
from pathlib import Path
from app.core.config import DOCS_DIR
from app.core.database import fetch_all, execute, log_action
from app.services.dataset_service import dashboard_metrics, get_project
from app.services.rework_service import list_reworks


def generate_report(project_id: int, report_type: str, username: str) -> Path:
    project = get_project(project_id)
    metrics = dashboard_metrics(project_id)
    reworks = list_reworks(project_id)
    issues = fetch_all("""SELECT qi.* FROM quality_issues qi JOIN samples s ON qi.sample_id=s.id WHERE s.project_id=? ORDER BY qi.severity DESC""", (project_id,))
    title = f"{project['name']} - {report_type}"
    path = DOCS_DIR / f"{project['code']}_{report_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    lines = [
        f"# 人工智能模型训练样本智能标注与质量校验管理软件 - {report_type}",
        "",
        f"报告标题：{title}",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"生成用户：{username}",
        "",
        "## 一、数据集概况",
        f"- 数据集名称：{project['name']}",
        f"- 样本数量：{metrics.get('sample_total', 0)}",
        f"- 已标注：{metrics.get('annotated_total', 0)}",
        f"- 待质检：{metrics.get('qc_pending_total', 0)}",
        f"- 返工数量：{metrics.get('rework_total', 0)}",
        f"- 数据集健康度：{metrics.get('health_score', 0)}",
        "",
        "## 二、核心质量指标",
        f"- 智能预标注采用率：{metrics.get('prelabel_adopt_rate', 0)}%",
        f"- 自动质检通过率：{metrics.get('auto_pass_rate', 0):.1f}%",
        f"- 人工质检通过率：{metrics.get('manual_pass_rate', 0):.1f}%",
        f"- 多人一致性评分：{metrics.get('consensus_score', 0):.1f}",
        f"- Ground Truth 抽检得分：{metrics.get('gt_score', 0):.1f}",
        f"- 标签均衡度：{metrics.get('balance_score', 0):.1f}",
        "",
        "## 三、高频质量问题",
    ]
    if issues:
        for i in issues[:20]:
            lines.append(f"- [{i['severity']}] {i['issue_type']}：{i['position_text']}；建议：{i['suggestion']}")
    else:
        lines.append("- 暂无未关闭质量问题。")
    lines.extend(["", "## 四、返工闭环", ""])
    if reworks:
        for r in reworks[:20]:
            lines.append(f"- {r['rework_code']}：{r['issue_type']}，状态：{r['status']}，要求：{r['requirement']}")
    else:
        lines.append("- 暂无返工任务。")
    lines.extend(["", "## 五、交付建议", ""])
    if metrics.get('health_score', 0) >= 90:
        conclusion = "可交付训练。"
    elif metrics.get('health_score', 0) >= 80:
        conclusion = "建议完成关键返工后交付。"
    else:
        conclusion = "存在明显质量风险，不建议直接交付训练。"
    lines.append(conclusion)
    for advice in metrics.get('health_advice', []):
        lines.append(f"- {advice}")
    path.write_text('\n'.join(lines), encoding='utf-8')
    execute("INSERT INTO reports(project_id,report_type,title,file_path,conclusion,created_by) VALUES(?,?,?,?,?,?)", (project_id, report_type, title, str(path), conclusion, username))
    log_action(username, '生成报告', f"{report_type} {path}")
    return path


def list_reports(project_id: int) -> list[dict]:
    return fetch_all("SELECT * FROM reports WHERE project_id=? ORDER BY id DESC", (project_id,))
