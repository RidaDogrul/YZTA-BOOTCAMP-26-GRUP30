import resend
from app.config import settings

resend.api_key = settings.RESEND_API_KEY


def send_manager_alert_email(subject: str, body: str) -> bool:
    """Yöneticiye e-posta uyarısı gönderir. Başarılıysa True döner."""
    if not settings.RESEND_API_KEY or not settings.MANAGER_EMAIL:
        return False  # Config eksikse sessizce fail et
    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [settings.MANAGER_EMAIL],
            "subject": subject,
            "text": body,
        })
        return True
    except Exception:
        return False
