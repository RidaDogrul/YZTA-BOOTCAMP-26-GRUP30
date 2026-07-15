from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import MessageRead

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", response_model=list[MessageRead])
def list_messages(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return crud.get_messages(db, limit=limit)
