from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import ShipmentRead

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("", response_model=list[ShipmentRead])
def list_shipments(db: Session = Depends(get_db)):
    return crud.get_shipments(db)
