from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import HealthResponse, SeedResponse
from app.seed import run_seed

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@router.post("/api/seed", response_model=SeedResponse)
def seed(db: Session = Depends(get_db)):
    counts = run_seed(db)
    return SeedResponse(seeded=True, counts=counts)
