from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import TaskRead, TaskStatusUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db)):
    return crud.get_tasks(db)


@router.patch("/{task_id}", response_model=TaskRead)
def update_status(task_id: int, body: TaskStatusUpdate, db: Session = Depends(get_db)):
    task = crud.update_task_status(db, task_id, body.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
