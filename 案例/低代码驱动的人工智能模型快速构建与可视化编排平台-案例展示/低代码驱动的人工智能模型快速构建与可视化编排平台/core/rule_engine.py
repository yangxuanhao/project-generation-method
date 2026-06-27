"""业务规则引擎 - 图形化条件配置、规则触发、冲突检测"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
import time, uuid, itertools

class TriggerType(Enum):
    DATA = "数据触发"
    TIMER = "定时触发"
    NODE = "流程节点触发"

class LogicOp(Enum):
    AND = "与"; OR = "或"; NOT = "非"

class CompareOp(Enum):
    EQ = "等于"; NE = "不等于"; GT = "大于"; LT = "小于"
    GTE = "大于等于"; LTE = "小于等于"; IN = "包含"; RE = "正则匹配"

@dataclass
class Condition:
    field: str; op: CompareOp; value: Any; logic: LogicOp = LogicOp.AND

@dataclass
class RuleAction:
    action_type: str; params: dict = field(default_factory=dict)

@dataclass
class Rule:
    rule_id: str; name: str; description: str = ""
    trigger: TriggerType = TriggerType.DATA
    conditions: List[Condition] = field(default_factory=list)
    actions: List[RuleAction] = field(default_factory=list)
    priority: int = 5; enabled: bool = True
    template_id: str = ""; group: str = "默认"

class RuleEngine:
    """原创规则引擎 - 条件组合、多触发方式、冲突检测、模板复用"""
    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._templates: Dict[str, Rule] = {}
        self._trigger_handlers: Dict[TriggerType, List[Callable]] = {
            t: [] for t in TriggerType}
        self._execution_log: List[dict] = []

    def create_rule(self, name: str, trigger: TriggerType, conditions: List[Condition],
                    actions: List[RuleAction], priority: int = 5, group: str = "默认") -> Rule:
        rid = f"R{str(uuid.uuid4())[:8]}"
        rule = Rule(rule_id=rid, name=name, trigger=trigger, conditions=conditions,
                    actions=actions, priority=max(1, min(10, priority)), group=group)
        self._rules[rid] = rule
        return rule

    def evaluate(self, rule_id: str, context: dict) -> bool:
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled: return False
        results = []
        for cond in rule.conditions:
            val = context.get(cond.field)
            r = self._compare(val, cond.op, cond.value)
            results.append(r)
        if not results: return True
        final = results[0]
        for i, cond in enumerate(rule.conditions[1:], 1):
            if cond.logic == LogicOp.AND:
                final = final and results[i]
            elif cond.logic == LogicOp.OR:
                final = final or results[i]
            elif cond.logic == LogicOp.NOT:
                final = final and not results[i]
        return final

    def evaluate_all(self, context: dict, trigger: TriggerType = None) -> List[Rule]:
        fired = []
        for rule in sorted(self._rules.values(), key=lambda r: -r.priority):
            if not rule.enabled: continue
            if trigger and rule.trigger != trigger: continue
            if self.evaluate(rule.rule_id, context):
                fired.append(rule)
                self._log(rule.rule_id, "FIRED", str(context)[:100])
        return fired

    def execute_actions(self, rule: Rule, context: dict) -> dict:
        results = {}
        for action in rule.actions:
            try:
                handler = self._get_action_handler(action.action_type)
                results[action.action_type] = handler(context, action.params)
            except Exception as e:
                results[action.action_type] = f"ERROR:{str(e)}"
        self._log(rule.rule_id, "EXECUTED", str(results)[:100])
        return results

    def detect_conflicts(self) -> List[dict]:
        """原创冲突检测算法 - 基于条件重叠图的规则冲突发现"""
        conflicts = []
        rules_list = list(self._rules.values())
        for i, j in itertools.combinations(range(len(rules_list)), 2):
            r1, r2 = rules_list[i], rules_list[j]
            if not r1.enabled or not r2.enabled: continue
            score = self._conflict_score(r1, r2)
            if score > 0.5:
                conflicts.append({"rule_a": r1.rule_id, "rule_b": r2.rule_id,
                    "score": score, "type": self._classify_conflict(r1, r2),
                    "detail": f"规则 [{r1.name}] 与 [{r2.name}] 存在{score:.0%}重叠"})
        return conflicts

    def save_as_template(self, rule_id: str, template_name: str) -> str:
        if rule_id not in self._rules: return ""
        tid = f"TPL_{str(uuid.uuid4())[:6]}"
        template = copy_rule(self._rules[rule_id])
        template.rule_id = tid; template.name = template_name
        template.template_id = tid
        self._templates[tid] = template
        return tid

    def create_from_template(self, template_id: str, name: str) -> Optional[Rule]:
        if template_id not in self._templates: return None
        new_rule = copy_rule(self._templates[template_id])
        new_rule.rule_id = f"R{str(uuid.uuid4())[:8]}"
        new_rule.name = name
        self._rules[new_rule.rule_id] = new_rule
        return new_rule

    def _conflict_score(self, r1: Rule, r2: Rule) -> float:
        fields1 = {c.field for c in r1.conditions}
        fields2 = {c.field for c in r2.conditions}
        if not fields1 & fields2: return 0.0
        shared = fields1 & fields2
        conflicting = 0
        for field in shared:
            c1 = next((c for c in r1.conditions if c.field == field), None)
            c2 = next((c for c in r2.conditions if c.field == field), None)
            if c1 and c2:
                if c1.op != c2.op or c1.value != c2.value:
                    conflicting += 1
        return conflicting / len(shared) if shared else 0.0

    def _classify_conflict(self, r1: Rule, r2: Rule) -> str:
        if r1.trigger != r2.trigger: return "触发方式冲突"
        actions1 = {a.action_type for a in r1.actions}
        actions2 = {a.action_type for a in r2.actions}
        if actions1 & actions2: return "动作冲突"
        return "条件重叠"

    def _compare(self, value: Any, op: CompareOp, target: Any) -> bool:
        try:
            if op == CompareOp.EQ: return value == target
            if op == CompareOp.NE: return value != target
            if op == CompareOp.GT: return float(value) > float(target)
            if op == CompareOp.LT: return float(value) < float(target)
            if op == CompareOp.GTE: return float(value) >= float(target)
            if op == CompareOp.LTE: return float(value) <= float(target)
            if op == CompareOp.IN: return target in str(value)
            if op == CompareOp.RE:
                import re; return bool(re.search(str(target), str(value)))
        except: return False
        return False

    def _get_action_handler(self, action_type: str):
        return self._action_handlers

    def _log(self, rule_id: str, event: str, detail: str):
        self._execution_log.append({"ts": time.time(), "rule_id": rule_id,
            "event": event, "detail": detail})

    def get_rules(self, trigger: TriggerType = None) -> List[Rule]:
        rules = list(self._rules.values())
        if trigger: rules = [r for r in rules if r.trigger == trigger]
        return sorted(rules, key=lambda r: -r.priority)

    def delete_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def toggle_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = not self._rules[rule_id].enabled
            return True
        return False

    _action_handlers = {
        "alert": lambda ctx, p: f"告警:{p.get('msg','')}",
        "abort": lambda ctx, p: "流程中止",
        "log": lambda ctx, p: f"日志:{p.get('text','')}",
        "transform": lambda ctx, p: {k: ctx.get(k, v) for k, v in p.items() if k != 'action_type'},
        "route": lambda ctx, p: f"路由到:{p.get('target','')}",
    }

def copy_rule(r: Rule) -> Rule:
    import copy
    return copy.deepcopy(r)

rule_engine = RuleEngine()
