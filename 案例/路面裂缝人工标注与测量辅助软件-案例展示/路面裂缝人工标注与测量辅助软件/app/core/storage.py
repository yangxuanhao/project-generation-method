from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Optional
from .models import User, AnnotationTask


class StorageManager:
    """本地JSON存储。演示系统不依赖数据库，便于直接运行。"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.data_dir / "users.json"
        self.tasks_path = self.data_dir / "tasks.json"
        self._ensure_files()

    def _ensure_files(self):
        if not self.users_path.exists():
            admin = User(username="admin", password_hash=self.hash_password("admin123"), role="管理员")
            self.users_path.write_text(json.dumps([admin.to_dict()], ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.tasks_path.exists():
            self.tasks_path.write_text("[]", encoding="utf-8")

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256((password + "road_crack_salt").encode("utf-8")).hexdigest()

    def load_users(self) -> List[User]:
        try:
            data = json.loads(self.users_path.read_text(encoding="utf-8"))
            return [User.from_dict(x) for x in data]
        except Exception:
            return []

    def save_users(self, users: List[User]):
        self.users_path.write_text(json.dumps([u.to_dict() for u in users], ensure_ascii=False, indent=2), encoding="utf-8")

    def register_user(self, username: str, password: str, role: str = "标注员") -> tuple[bool, str]:
        username = username.strip()
        if len(username) < 2:
            return False, "用户名至少需要2个字符"
        if len(password) < 6:
            return False, "密码至少需要6位"
        users = self.load_users()
        if any(u.username == username for u in users):
            return False, "用户名已存在"
        users.append(User(username=username, password_hash=self.hash_password(password), role=role))
        self.save_users(users)
        return True, "注册成功"

    def verify_user(self, username: str, password: str) -> Optional[User]:
        hashed = self.hash_password(password)
        for user in self.load_users():
            if user.username == username and user.password_hash == hashed:
                return user
        return None

    def load_tasks(self) -> List[AnnotationTask]:
        try:
            data = json.loads(self.tasks_path.read_text(encoding="utf-8"))
            return [AnnotationTask.from_dict(x) for x in data]
        except Exception:
            return []

    def save_tasks(self, tasks: List[AnnotationTask]):
        self.tasks_path.write_text(json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert_task(self, task: AnnotationTask):
        tasks = self.load_tasks()
        found = False
        for i, old in enumerate(tasks):
            if old.task_id == task.task_id:
                task.touch()
                tasks[i] = task
                found = True
                break
        if not found:
            tasks.append(task)
        self.save_tasks(tasks)
