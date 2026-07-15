from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.ai_service import process_chat

router = APIRouter(prefix="/api/chat", tags=["ai"])

@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return process_chat(req.message, db)
