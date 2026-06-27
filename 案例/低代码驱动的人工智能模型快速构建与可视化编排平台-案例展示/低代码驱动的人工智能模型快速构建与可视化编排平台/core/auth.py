"""RBAC认证授权引擎 - 多角色权限调度与会话状态流转"""
import hashlib, json, time, uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable

class Role(Enum):
    ADMIN = "管理员"
    DEVELOPER = "模型开发者"
    OPERATOR = "普通操作员"
    GUEST = "访客"

class SessionState(Enum):
    ACTIVE = "活跃"
    IDLE = "空闲"
    LOCKED = "锁定"
    EXPIRED = "过期"

class OpAction(Enum):
    VIEW = "查看"
    CREATE = "创建"
    EDIT = "编辑"
    DELETE = "删除"
    EXECUTE = "执行"
    EXPORT = "导出"
    ADMIN = "管理"

@dataclass
class Permission:
    resource: str
    actions: Set[OpAction] = field(default_factory=set)

@dataclass
class User:
    uid: str; username: str; password_hash: str; role: Role
    permissions: List[Permission] = field(default_factory=list)
    login_attempts: int = 0; locked_until: float = 0; last_login: float = 0

class RBACEngine:
    """原创RBAC权限调度引擎 - 支持粒度权限控制、批量分配、权限回收、操作审计"""
    ROLE_DEFAULTS = {
        Role.ADMIN: ["*"],
        Role.DEVELOPER: ["dashboard", "model_designer", "lowcode_editor", "model_training",
                        "vision_lab", "vision_3d", "data_manager", "task_manager",
                        "project_manager", "component_market", "report_center"],
        Role.OPERATOR: ["dashboard", "model_training", "vision_lab", "data_manager", "task_manager", "report_center"],
        Role.GUEST: ["dashboard", "report_center"],
    }

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, dict] = {}
        self._audit_log: List[dict] = []
        self._perm_change_callbacks: List[Callable] = []
        self._init_default_users()

    def _hash(self, pwd: str) -> str:
        return hashlib.sha256(f"AILab_Salt_{pwd}_2024".encode()).hexdigest()

    def _init_default_users(self):
        for role, (uname, pwd) in {
            Role.ADMIN: ("admin", "admin123"),
            Role.DEVELOPER: ("developer", "dev123"),
            Role.OPERATOR: ("operator", "op123"),
            Role.GUEST: ("guest", "guest123"),
        }.items():
            self.register(uname, pwd, role)

    def register(self, username: str, password: str, role: Role = Role.GUEST) -> Optional[User]:
        if any(u.username == username for u in self._users.values()):
            return None
        user = User(uid=str(uuid.uuid4())[:8], username=username,
                    password_hash=self._hash(password), role=role)
        user.permissions = self._build_permissions(role)
        self._users[user.uid] = user
        self._log("REGISTER", user.uid, f"用户注册: {username} 角色: {role.value}")
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username != username: continue
            if time.time() < user.locked_until:
                self._log("LOGIN_BLOCKED", user.uid, "账号锁定中")
                return None
            if self._hash(password) == user.password_hash:
                if user.login_attempts >= 5 and time.time() - user.last_login < 300:
                    user.locked_until = time.time() + 600
                    self._log("LOGIN_LOCKED", user.uid, "多次失败锁定10分钟")
                    return None
                user.login_attempts = 0; user.last_login = time.time()
                sid = str(uuid.uuid4())[:12]
                self._sessions[sid] = {"uid": user.uid, "state": SessionState.ACTIVE,
                    "created": time.time(), "last_active": time.time()}
                self._log("LOGIN_SUCCESS", user.uid, f"登录成功 sid={sid}")
                return user
            user.login_attempts += 1
            self._log("LOGIN_FAIL", user.uid, f"密码错误 尝试#{user.login_attempts}")
        return None

    def check_permission(self, user: User, resource: str, action: OpAction) -> bool:
        if user.role == Role.ADMIN: return True
        for perm in user.permissions:
            if perm.resource == resource or perm.resource == "*":
                return action in perm.actions or OpAction.ADMIN in perm.actions
        return False

    def grant_permission(self, admin: User, target_uid: str, resource: str, actions: Set[OpAction]) -> bool:
        if admin.role != Role.ADMIN: return False
        if target_uid not in self._users: return False
        target = self._users[target_uid]
        for perm in target.permissions:
            if perm.resource == resource:
                perm.actions.update(actions); break
        else:
            target.permissions.append(Permission(resource=resource, actions=actions))
        self._log("PERM_GRANT", admin.uid, f"授权 {target_uid} -> {resource}: {[a.value for a in actions]}")
        self._notify_perm_change()
        return True

    def revoke_permission(self, admin: User, target_uid: str, resource: str) -> bool:
        if admin.role != Role.ADMIN: return False
        if target_uid not in self._users: return False
        self._users[target_uid].permissions = [p for p in self._users[target_uid].permissions if p.resource != resource]
        self._log("PERM_REVOKE", admin.uid, f"回收 {target_uid} -> {resource}")
        self._notify_perm_change()
        return True

    def batch_grant(self, admin: User, target_uids: List[str], resources: List[str], actions: Set[OpAction]) -> bool:
        if admin.role != Role.ADMIN: return False
        results = []
        for uid in target_uids:
            for res in resources:
                results.append(self.grant_permission(admin, uid, res, actions))
        return all(results)

    def get_audit_log(self, uid_filter: str = None, limit: int = 100) -> List[dict]:
        logs = self._audit_log
        if uid_filter:
            logs = [l for l in logs if l.get("uid") == uid_filter]
        return logs[-limit:]

    def validate_session(self, sid: str) -> Optional[User]:
        if sid not in self._sessions: return None
        session = self._sessions[sid]
        if time.time() - session["last_active"] > 3600:
            session["state"] = SessionState.EXPIRED
            return None
        session["last_active"] = time.time()
        return self._users.get(session["uid"])

    def transition_session(self, sid: str, new_state: SessionState) -> bool:
        if sid not in self._sessions: return False
        valid_transitions = {
            SessionState.ACTIVE: [SessionState.IDLE],
            SessionState.IDLE: [SessionState.ACTIVE, SessionState.LOCKED, SessionState.EXPIRED],
            SessionState.LOCKED: [SessionState.ACTIVE, SessionState.EXPIRED],
            SessionState.EXPIRED: [SessionState.ACTIVE],
        }
        current = self._sessions[sid]["state"]
        if new_state in valid_transitions.get(current, []):
            self._sessions[sid]["state"] = new_state
            self._log("SESSION", sid, f"状态流转: {current.value} -> {new_state.value}")
            return True
        return False

    def _build_permissions(self, role: Role) -> List[Permission]:
        resources = self.ROLE_DEFAULTS.get(role, [])
        perms = []
        for res in resources:
            if res == "*":
                perms.append(Permission(resource="*", actions={OpAction.ADMIN}))
            else:
                perms.append(Permission(resource=res, actions={
                    OpAction.VIEW, OpAction.CREATE, OpAction.EDIT, OpAction.EXECUTE}))
        return perms

    def _log(self, action: str, uid: str, detail: str):
        self._audit_log.append({"ts": time.time(), "action": action, "uid": uid, "detail": detail})

    def _notify_perm_change(self):
        for cb in self._perm_change_callbacks: cb()

    def on_perm_change(self, callback: Callable):
        self._perm_change_callbacks.append(callback)

    def get_all_users(self) -> List[User]:
        return list(self._users.values())

    def get_user_by_uid(self, uid: str) -> Optional[User]:
        return self._users.get(uid)

# 全局单例
auth_engine = RBACEngine()
