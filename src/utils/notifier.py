"""Tahmin tamamlanınca opsiyonel e-posta ve Slack bildirimi gönderir."""

from __future__ import annotations

import json
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

from src.utils.config import get_settings
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.ml_models.forecaster import ForecastResult


logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """Bildirimlerin gönderim sonucunu tutar."""

    email_sent: bool = False
    slack_sent: bool = False
    errors: list[str] = field(default_factory=list)


def _forecast_summary(result: ForecastResult) -> tuple[str, str]:
    """Tahmin sonucundan bildirim metni oluşturur."""

    forecast = result.forecast
    horizon = len(forecast)

    first_value = float(forecast["yhat"].iloc[0])
    last_value = float(forecast["yhat"].iloc[-1])

    change = 0.0
    if first_value != 0:
        change = ((last_value - first_value) / abs(first_value)) * 100

    mape = result.model_scores.get(result.selected_model)

    accuracy_line = ""
    if mape is not None:
        accuracy_line = f"\nDoğrulama MAPE: {mape:.2f}%"

    subject = f"Tahmin tamamlandı — {result.selected_model.upper()}"

    body = (
        "Tahminleme işlemi başarıyla tamamlandı.\n\n"
        f"Seçilen model: {result.selected_model}\n"
        f"Tahmin ufku: {horizon} gün\n"
        f"İlk tahmin: {first_value:,.2f}\n"
        f"Son tahmin: {last_value:,.2f}\n"
        f"Değişim: {change:+.2f}%"
        f"{accuracy_line}"
    )

    return subject, body


def _send_email(subject: str, body: str, settings: Any) -> None:
    """SMTP kullanarak e-posta gönderir."""

    required_values = (
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.smtp_from,
        settings.notification_email_to,
    )

    if not all(required_values):
        raise ValueError("E-posta bildirimi için SMTP ayarları eksik.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = settings.notification_email_to
    message.set_content(body)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=10,
    ) as client:
        client.starttls()
        client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


def _send_slack(subject: str, body: str, settings: Any) -> None:
    """Slack webhook kullanarak kanal mesajı gönderir."""

    if not settings.slack_webhook_url:
        raise ValueError("Slack bildirimi için SLACK_WEBHOOK_URL eksik.")

    payload = json.dumps(
        {"text": f"*{subject}*\n{body}"}
    ).encode("utf-8")

    request = Request(
        settings.slack_webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(
                f"Slack HTTP durum kodu: {response.status}"
            )


def notify_forecast_completed(result: ForecastResult) -> NotificationResult:
    """
    Tahmin tamamlandıktan sonra yapılandırılmış kanallara bildirim gönderir.

    Bildirim hatası tahmini bozmaz; hata sadece loglanır.
    """

    settings = get_settings()
    delivery = NotificationResult()

    if not settings.notification_enabled:
        return delivery

    subject, body = _forecast_summary(result)

    if settings.notification_email_to:
        try:
            _send_email(subject, body, settings)
            delivery.email_sent = True
        except Exception as exc:
            delivery.errors.append(f"email: {exc}")
            logger.warning(
                "Tahmin e-posta bildirimi gönderilemedi",
                extra={"error": str(exc)},
            )

    if settings.slack_webhook_url:
        try:
            _send_slack(subject, body, settings)
            delivery.slack_sent = True
        except Exception as exc:
            delivery.errors.append(f"slack: {exc}")
            logger.warning(
                "Tahmin Slack bildirimi gönderilemedi",
                extra={"error": str(exc)},
            )

    if not settings.notification_email_to and not settings.slack_webhook_url:
        logger.warning(
            "Bildirim açık ancak hedef kanal yapılandırılmamış."
        )

    return delivery