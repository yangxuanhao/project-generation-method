"""数据一致性引擎 - 事务管理、快照回溯、MVCC式数据版本控制"""
import time, uuid, copy, threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

class TxnStatus(Enum):
    ACTIVE = "活跃"
    COMMITTED = "已提交"
    ROLLED_BACK = "已回滚"

@dataclass
class DataSnapshot:
    snap_id: str; flow_id: str; node_id: str; data: Any
    timestamp: float; version: int; checksum: str = ""

class DataTransaction:
    def __init__(self, txn_id: str, flow_id: str):
        self.txn_id = txn_id; self.flow_id = flow_id
        self.status = TxnStatus.ACTIVE; self.operations: List[dict] = []
        self.created = time.time()

class DataConsistencyEngine:
    """原创数据一致性引擎 - 事务锁定、异常回滚、快照管理、版本强一致性校验"""
    def __init__(self):
        self._data_store: Dict[str, dict] = {}
        self._snapshots: Dict[str, List[DataSnapshot]] = {}
        self._txns: Dict[str, DataTransaction] = {}
        self._locks: Dict[str, str] = {}
        self._lock = threading.RLock()
        self._version_counter: Dict[str, int] = {}
        self._integrity_rules: List[Callable] = []

    def register_node(self, flow_id: str, node_id: str, initial_data: Any = None):
        key = f"{flow_id}:{node_id}"
        with self._lock:
            self._data_store[key] = {"data": initial_data, "version": 1, "checksum": self._checksum(initial_data)}
            self._version_counter.setdefault(flow_id, 0)
            self._save_snapshot(flow_id, node_id, initial_data, 1)

    def begin_transaction(self, flow_id: str) -> DataTransaction:
        txn = DataTransaction(f"TXN_{uuid.uuid4().hex[:8]}", flow_id)
        with self._lock: self._txns[txn.txn_id] = txn
        return txn

    def write(self, txn: DataTransaction, node_id: str, data: Any) -> bool:
        if txn.status != TxnStatus.ACTIVE: return False
        key = f"{txn.flow_id}:{node_id}"
        with self._lock:
            if key in self._locks and self._locks[key] != txn.txn_id: return False
            self._locks[key] = txn.txn_id
            current = self._data_store.get(key, {"data": None, "version": 0})
            new_version = current["version"] + 1
            txn.operations.append({"node_id": node_id, "old": copy.deepcopy(current["data"]),
                "new": copy.deepcopy(data), "version": new_version, "key": key})
        return True

    def commit(self, txn: DataTransaction) -> bool:
        if txn.status != TxnStatus.ACTIVE: return False
        with self._lock:
            try:
                for op in txn.operations:
                    key = op["key"]
                    if not self._validate_integrity(key, op["new"]): raise ValueError("完整性校验失败")
                    self._data_store[key] = {"data": op["new"], "version": op["version"],
                        "checksum": self._checksum(op["new"])}
                    self._save_snapshot(txn.flow_id, op["node_id"], op["new"], op["version"])
                    self._locks.pop(key, None)
                txn.status = TxnStatus.COMMITTED
                return True
            except Exception:
                self.rollback(txn); return False

    def rollback(self, txn: DataTransaction) -> bool:
        with self._lock:
            for op in reversed(txn.operations):
                key = op["key"]
                if op["version"] > 1:
                    self._data_store[key] = {"data": op["old"], "version": op["version"] - 1,
                        "checksum": self._checksum(op["old"])}
                self._locks.pop(key, None)
            txn.status = TxnStatus.ROLLED_BACK
        return True

    def get_snapshot(self, flow_id: str, node_id: str = None, version: int = None) -> Any:
        key = f"{flow_id}:{node_id}" if node_id else None
        if key:
            store = self._data_store.get(key)
            return store["data"] if store else None
        snapshots = self._snapshots.get(flow_id, [])
        if version:
            snapshots = [s for s in snapshots if s.version == version]
        return snapshots[-1].data if snapshots else None

    def export_snapshot(self, flow_id: str, version: int = None) -> dict:
        snapshots = self._snapshots.get(flow_id, [])
        if version: snapshots = [s for s in snapshots if s.version == version]
        return {"flow_id": flow_id, "snapshots": [
            {"node": s.node_id, "version": s.version, "data": s.data, "checksum": s.checksum}
            for s in snapshots]}

    def load_snapshot(self, snapshot_data: dict) -> bool:
        flow_id = snapshot_data["flow_id"]
        with self._lock:
            for snap in snapshot_data["snapshots"]:
                key = f"{flow_id}:{snap['node']}"
                self._data_store[key] = {"data": snap["data"], "version": snap["version"],
                    "checksum": snap["checksum"]}
            return True

    def verify_consistency(self, flow_id: str) -> dict:
        """强一致性校验 - 比对所有节点checksum确保数据完整性"""
        results = {"flow_id": flow_id, "consistent": True, "issues": []}
        for key, store in self._data_store.items():
            if key.startswith(flow_id):
                actual = self._checksum(store["data"])
                if actual != store["checksum"]:
                    results["consistent"] = False
                    results["issues"].append({"node": key, "expected": store["checksum"], "actual": actual})
        return results

    def add_integrity_rule(self, rule: Callable[[str, Any], bool]):
        self._integrity_rules.append(rule)

    def _validate_integrity(self, key: str, data: Any) -> bool:
        return all(rule(key, data) for rule in self._integrity_rules) if self._integrity_rules else True

    def _save_snapshot(self, flow_id: str, node_id: str, data: Any, version: int):
        snap = DataSnapshot(snap_id=uuid.uuid4().hex[:8], flow_id=flow_id,
            node_id=node_id, data=copy.deepcopy(data), timestamp=time.time(),
            version=version, checksum=self._checksum(data))
        self._snapshots.setdefault(flow_id, []).append(snap)

    @staticmethod
    def _checksum(data: Any) -> str:
        import hashlib, json
        try: return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:8]
        except: return "00000000"

    def get_node_history(self, flow_id: str, node_id: str) -> List[DataSnapshot]:
        return [s for s in self._snapshots.get(flow_id, []) if s.node_id == node_id]

data_engine = DataConsistencyEngine()
