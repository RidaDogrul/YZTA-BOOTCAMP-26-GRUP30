from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dashboard_service import get_summary
from app.database import get_db
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    return get_summary(db)
