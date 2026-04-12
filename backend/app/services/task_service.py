from typing import List

from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskStatus


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, data: TaskCreate, user_id: int) -> Task:
        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            status=TaskStatus.PENDING.value,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_status(self, task_id: int, status: TaskStatus, result: str | None = None) -> Task | None:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status.value
            if result is not None:
                task.result = result
            self.db.commit()
            self.db.refresh(task)
        return task

    def get_user_tasks(self, user_id: int, limit: int = 50) -> List[Task]:
        return (
            self.db.query(Task)
            .filter(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .all()
        )
