from types import SimpleNamespace

import pandas as pd

import src.utils.notifier as notifier


def _forecast_result():
    """Test için örnek tahmin sonucu oluşturur."""

    return SimpleNamespace(
        selected_model="arima",
        model_scores={"arima": 8.5},
        forecast=pd.DataFrame(
            {
                "yhat": [100.0, 115.0],
            }
        ),
    )


def test_disabled_notifications_do_not_send(monkeypatch):
    """Bildirim kapalıyken e-posta veya Slack isteği gönderilmez."""

    settings = SimpleNamespace(notification_enabled=False)

    monkeypatch.setattr(
        notifier,
        "get_settings",
        lambda: settings,
    )

    result = notifier.notify_forecast_completed(_forecast_result())

    assert result.email_sent is False
    assert result.slack_sent is False
    assert result.errors == []


def test_forecast_summary_contains_model_and_horizon():
    """Bildirim metninin tahmin bilgilerini taşıdığını kontrol eder."""

    subject, body = notifier._forecast_summary(_forecast_result())

    assert "ARIMA" in subject
    assert "2 gün" in body
    assert "15.00%" in body