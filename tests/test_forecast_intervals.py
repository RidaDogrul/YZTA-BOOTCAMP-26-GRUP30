from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

import src.ml_models.forecaster as forecaster_module
from src.ml_models.forecaster import (
    ForecastConfig,
    _build_forecast_frame,
    create_future_dates,
    forecast_arima,
    forecast_lightgbm,
    forecast_prophet,
    model_selector,
)


INTERVAL_COLUMNS = [
    "ds",
    "yhat",
    "yhat_lower_80",
    "yhat_upper_80",
    "yhat_lower_95",
    "yhat_upper_95",
]


def build_sample_time_series(periods: int = 120) -> pd.DataFrame:
    """Trend ve haftalık mevsimsellik içeren yapay satış verisi üretir."""
    day_numbers = np.arange(periods)
    trend = 100 + (day_numbers * 0.8)
    weekly_seasonality = np.sin(2 * np.pi * day_numbers / 7) * 12
    values = trend + weekly_seasonality

    return pd.DataFrame(
        {
            "ds": pd.date_range(start="2026-01-01", periods=periods, freq="D"),
            "y": values,
        }
    )


def assert_valid_prediction_intervals(result: pd.DataFrame) -> None:
    """Tahmin bantlarının sonlu, iç içe ve yhat değerini kapsadığını doğrular."""
    assert list(result.columns) == INTERVAL_COLUMNS
    assert result[INTERVAL_COLUMNS[1:]].notna().all().all()
    assert np.isfinite(result[INTERVAL_COLUMNS[1:]].to_numpy()).all()

    assert (result["yhat_lower_95"] <= result["yhat_lower_80"]).all()
    assert (result["yhat_lower_80"] <= result["yhat"]).all()
    assert (result["yhat"] <= result["yhat_upper_80"]).all()
    assert (result["yhat_upper_80"] <= result["yhat_upper_95"]).all()


def test_forecast_config_rejects_invalid_uncertainty_sample_count() -> None:
    with pytest.raises(ValueError, match="prophet_uncertainty_samples"):
        ForecastConfig(prophet_uncertainty_samples=0)


def test_build_forecast_frame_keeps_legacy_shape_without_intervals() -> None:
    dates = pd.date_range(start="2026-01-01", periods=2, freq="D")

    result = _build_forecast_frame(
        prediction_dates=dates,
        predictions=[100.0, 110.0],
    )

    assert list(result.columns) == ["ds", "yhat"]


def test_build_forecast_frame_normalizes_crossed_intervals() -> None:
    dates = pd.date_range(start="2026-01-01", periods=2, freq="D")

    result = _build_forecast_frame(
        prediction_dates=dates,
        predictions=[100.0, 110.0],
        prediction_intervals={
            80: ([90.0, 100.0], [110.0, 120.0]),
            95: ([95.0, 105.0], [105.0, 115.0]),
        },
    )

    assert_valid_prediction_intervals(result)
    assert list(result["yhat_lower_95"]) == [90.0, 100.0]
    assert list(result["yhat_upper_95"]) == [110.0, 120.0]


def test_build_forecast_frame_rejects_missing_interval_level() -> None:
    dates = pd.date_range(start="2026-01-01", periods=2, freq="D")

    with pytest.raises(ValueError, match="Eksik tahmin aralığı"):
        _build_forecast_frame(
            prediction_dates=dates,
            predictions=[100.0, 110.0],
            prediction_intervals={
                80: ([90.0, 100.0], [110.0, 120.0]),
            },
        )


@pytest.mark.parametrize(
    "forecast_function",
    [forecast_prophet, forecast_arima, forecast_lightgbm],
    ids=["prophet", "arima", "lightgbm"],
)
def test_forecast_models_produce_80_and_95_intervals(
    forecast_function: Callable[..., pd.DataFrame],
) -> None:
    time_series = build_sample_time_series()
    config = ForecastConfig(
        forecast_days=7,
        include_prediction_intervals=True,
        prophet_uncertainty_samples=300,
    )
    future_dates = create_future_dates(time_series, config=config)

    result = forecast_function(
        train=time_series,
        prediction_dates=future_dates,
        config=config,
    )

    assert len(result) == 7
    assert list(result["ds"]) == list(future_dates)
    assert_valid_prediction_intervals(result)


def test_model_selector_adds_intervals_only_to_final_forecast(monkeypatch) -> None:
    time_series = build_sample_time_series(periods=100)
    source = time_series.rename(columns={"ds": "date", "y": "sales"})
    interval_flags: list[bool] = []

    def fake_forecast(model_name, train, prediction_dates, config):
        dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
        interval_flags.append(config.include_prediction_intervals)
        prediction_value = {
            "prophet": 140.0,
            "arima": 142.0,
            "lightgbm": 145.0,
        }[model_name]
        result = pd.DataFrame(
            {
                "ds": dates,
                "yhat": np.full(len(dates), prediction_value),
            }
        )

        if config.include_prediction_intervals:
            result["yhat_lower_80"] = result["yhat"] - 10
            result["yhat_upper_80"] = result["yhat"] + 10
            result["yhat_lower_95"] = result["yhat"] - 20
            result["yhat_upper_95"] = result["yhat"] + 20

        return result

    monkeypatch.setattr(
        forecaster_module,
        "_forecast_with_model",
        fake_forecast,
    )

    result = model_selector(
        df=source,
        date_column="date",
        target_column="sales",
        config=ForecastConfig(
            forecast_days=7,
            include_prediction_intervals=True,
        ),
    )

    assert interval_flags[:3] == [False, False, False]
    assert interval_flags[-1] is True
    assert len(result.forecast) == 7
    assert_valid_prediction_intervals(result.forecast)
