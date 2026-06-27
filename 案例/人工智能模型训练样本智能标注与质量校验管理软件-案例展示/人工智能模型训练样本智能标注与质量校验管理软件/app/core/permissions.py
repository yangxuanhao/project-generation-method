ROLE_MENUS = {
    "管理员": "all",
    "项目经理": ["数据集驾驶舱", "数据集项目管理", "质量校验中心", "多人一致性分析", "Ground Truth 抽检", "返工闭环管理", "数据集版本管理", "报告生成中心", "操作日志"],
    "标注员": ["数据集驾驶舱", "样本标注生产工作台", "文本标注工作台", "返工闭环管理"],
    "质检员": ["数据集驾驶舱", "质量校验中心", "多人一致性分析", "Ground Truth 抽检", "返工闭环管理", "报告生成中心"],
}


def can_access(role: str, menu_name: str) -> bool:
    allowed = ROLE_MENUS.get(role, [])
    return allowed == "all" or menu_name in allowed
