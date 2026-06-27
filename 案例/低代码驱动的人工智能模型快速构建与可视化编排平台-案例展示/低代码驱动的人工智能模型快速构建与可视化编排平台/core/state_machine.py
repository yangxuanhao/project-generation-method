"""状态流转引擎 - 编排流程五态管理、状态锁定与回滚"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import time, copy, uuid

class FlowState(Enum):
    EDITING = "编辑态"
    DEBUGGING = "调试态"
    RUNNING = "运行态"
    PAUSED = "暂停态"
    ABORTED = "异常终止态"

class TaskState(Enum):
    QUEUED = "排队中"
    PREPARING = "准备中"
    EXECUTING = "执行中"
    PAUSED = "已暂停"
    COMPLETED = "已完成"
    FAILED = "已失败"
    CANCELLED = "已取消"

@dataclass
class StateSnapshot:
    state_id: str; flow_id: str; state: FlowState; data: dict
    timestamp: float; node_states: dict = field(default_factory=dict)

class FlowStateMachine:
    """原创流程状态机 - 编辑/调试/运行/暂停/异常终止五大状态流转"""
    VALID_TRANSITIONS = {
        FlowState.EDITING: [FlowState.DEBUGGING, FlowState.ABORTED],
        FlowState.DEBUGGING: [FlowState.EDITING, FlowState.RUNNING, FlowState.ABORTED],
        FlowState.RUNNING: [FlowState.PAUSED, FlowState.ABORTED, FlowState.EDITING],
        FlowState.PAUSED: [FlowState.RUNNING, FlowState.EDITING, FlowState.ABORTED],
        FlowState.ABORTED: [FlowState.EDITING],
    }

    def __init__(self):
        self._flows: Dict[str, dict] = {}
        self._snapshots: Dict[str, List[StateSnapshot]] = {}
        self._locks: Dict[str, str] = {}
        self._listeners: List[Callable] = []

    def create_flow(self, flow_id: str, metadata: dict = None) -> str:
        self._flows[flow_id] = {"state": FlowState.EDITING, "nodes": {},
            "meta": metadata or {}, "created": time.time(), "version": 1}
        self._snapshots[flow_id] = []
        self._notify(flow_id, FlowState.EDITING, None)
        return flow_id

    def get_state(self, flow_id: str) -> Optional[FlowState]:
        flow = self._flows.get(flow_id)
        return flow["state"] if flow else None

    def transition(self, flow_id: str, target: FlowState, operator: str = "") -> bool:
        flow = self._flows.get(flow_id)
        if not flow: return False
        current = flow["state"]
        if target not in self.VALID_TRANSITIONS.get(current, []): return False
        if self._locks.get(flow_id) and self._locks[flow_id] != operator: return False
        self._save_snapshot(flow_id)
        flow["state"] = target
        flow["version"] += 1
        self._notify(flow_id, target, current)
        return True

    def lock(self, flow_id: str, operator: str) -> bool:
        if flow_id in self._locks: return False
        self._locks[flow_id] = operator
        return True

    def unlock(self, flow_id: str, operator: str) -> bool:
        if self._locks.get(flow_id) == operator:
            del self._locks[flow_id]; return True
        return False

    def rollback(self, flow_id: str) -> bool:
        flow = self._flows.get(flow_id)
        if not flow: return False
        snapshots = self._snapshots.get(flow_id, [])
        if not snapshots: return False
        snapshot = snapshots[-1]
        flow["state"] = snapshot.state
        flow["nodes"] = snapshot.node_states.copy()
        flow["version"] = max(1, flow["version"] - 1)
        self._notify(flow_id, flow["state"], None)
        return True

    def _save_snapshot(self, flow_id: str):
        flow = self._flows[flow_id]
        snap = StateSnapshot(state_id=str(uuid.uuid4())[:8], flow_id=flow_id,
            state=flow["state"], data=copy.deepcopy(flow.get("meta", {})),
            timestamp=time.time(), node_states=copy.deepcopy(flow.get("nodes", {})))
        self._snapshots.setdefault(flow_id, []).append(snap)

    def get_snapshots(self, flow_id: str) -> List[StateSnapshot]:
        return self._snapshots.get(flow_id, [])

    def on_state_change(self, callback: Callable):
        self._listeners.append(callback)

    def _notify(self, flow_id, new_state, old_state):
        for cb in self._listeners:
            try: cb(flow_id, new_state, old_state)
            except: pass

class TaskStateMachine:
    """任务状态流转引擎 - 排队/准备/执行/暂停/完成/失败/取消七态管理"""
    TRANSITIONS = {
        TaskState.QUEUED: [TaskState.PREPARING, TaskState.CANCELLED],
        TaskState.PREPARING: [TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.EXECUTING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.PAUSED: [TaskState.EXECUTING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.FAILED: [TaskState.QUEUED, TaskState.CANCELLED],
    }

    def __init__(self):
        self._tasks: Dict[str, dict] = {}
        self._listeners: List[Callable] = []

    def create_task(self, task_id: str, task_type: str, priority: int = 5) -> str:
        self._tasks[task_id] = {"state": TaskState.QUEUED, "type": task_type,
            "priority": min(10, max(1, priority)), "created": time.time(),
            "started": 0, "finished": 0, "error": None}
        return task_id

    def transition(self, task_id: str, target: TaskState, error: str = None) -> bool:
        task = self._tasks.get(task_id)
        if not task: return False
        if target not in self.TRANSITIONS.get(task["state"], []): return False
        task["state"] = target
        if target == TaskState.EXECUTING: task["started"] = time.time()
        if target in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            task["finished"] = time.time()
        task["error"] = error
        self._notify(task_id, target)
        return True

    def get_state(self, task_id: str) -> Optional[TaskState]:
        t = self._tasks.get(task_id); return t["state"] if t else None

    def on_transition(self, callback: Callable):
        self._listeners.append(callback)

    def _notify(self, task_id, state):
        for cb in self._listeners:
            try: cb(task_id, state)
            except: pass

    def get_tasks_by_state(self, state: TaskState) -> List[dict]:
        return [{"id": tid, **t} for tid, t in self._tasks.items() if t["state"] == state]

    def get_all_tasks(self) -> List[dict]:
        return [{"id": tid, **t} for tid, t in self._tasks.items()]

flow_sm = FlowStateMachine()
task_sm = TaskStateMachine()
