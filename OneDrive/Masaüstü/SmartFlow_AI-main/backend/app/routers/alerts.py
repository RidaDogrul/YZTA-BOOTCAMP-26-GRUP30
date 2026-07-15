from fastapi import APIRouter, Body
from app.email_service import send_manager_alert_email

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.post("/send")
def send_alert(
    subject: str = Body(..., min_length=1),
    body: str = Body(..., min_length=1),
):
    ok = send_manager_alert_email(subject, body)
    return {"sent": ok}
