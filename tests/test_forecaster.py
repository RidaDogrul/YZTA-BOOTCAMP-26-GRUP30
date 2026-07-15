
import numpy as np
import pandas as pd
import pytest

import src.ml_models.forecaster as forecaster_module
from src.ml_models.forecaster import (
    ForecastConfig,
    ForecastResult,
    calculate_mape,
    create_future_dates,
    evaluate_forecast,
    forecast_arima,
    forecast_lightgbm,
    forecast_prophet,
    model_selector,
    prepare_time_series,
    split_time_series,
)


def build_sample_time_series(periods: int = 100) -> pd.DataFrame:
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


def test_prepare_time_series_sorts_and_aggregates_dates():
    df = pd.DataFrame(
        {
            "order_date": ["2026-01-03", "2026-01-01", "2026-01-01"],
            "sales": [30, 10, 5],
        }
    )

    result = prepare_time_series(
        df=df,
        date_column="order_date",
        target_column="sales",
    )

    assert list(result.columns) == ["ds", "y"]
    assert len(result) == 3
    assert result.loc[0, "ds"] == pd.Timestamp("2026-01-01")
    assert result.loc[0, "y"] == 15
    assert result.loc[1, "ds"] == pd.Timestamp("2026-01-02")
    assert result.loc[1, "y"] == 22.5
    assert result.loc[2, "ds"] == pd.Timestamp("2026-01-03")
    assert result.loc[2, "y"] == 30


def test_prepare_time_series_supports_mean_aggregation():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-01", "2026-01-02"],
            "value": [10, 20, 30],
        }
    )
    config = ForecastConfig(aggregation="mean")

    result = prepare_time_series(
        df=df,
        date_column="date",
        target_column="value",
        config=config,
    )

    assert result.loc[0, "y"] == 15
    assert result.loc[1, "y"] == 30


def test_prepare_time_series_rejects_empty_dataframe():
    with pytest.raises(ValueError, match="boş olamaz"):
        prepare_time_series(
            df=pd.DataFrame(),
            date_column="date",
            target_column="sales",
        )


def test_prepare_time_series_rejects_missing_columns():
    df = pd.DataFrame({"date": ["2026-01-01"], "sales": [100]})

    with pytest.raises(ValueError, match="Eksik DataFrame"):
        prepare_time_series(
            df=df,
            date_column="missing_date",
            target_column="sales",
        )


def test_prepare_time_series_rejects_invalid_dates():
    df = pd.DataFrame({"date": ["geçersiz", "tarih"], "sales": [100, 200]})

    with pytest.raises(ValueError, match="Geçerli bir tarih"):
        prepare_time_series(
            df=df,
            date_column="date",
            target_column="sales",
        )


def test_split_time_series_preserves_chronological_order():
    time_series = pd.DataFrame(
        {
            "ds": pd.date_range(start="2026-01-01", periods=100, freq="D"),
            "y": range(100),
        }
    )
    config = ForecastConfig(
        validation_days=30,
        min_train_size=45,
        min_validation_size=7,
    )

    train, validation = split_time_series(time_series, config=config)

    assert len(train) == 70
    assert len(validation) == 30
    assert train["ds"].max() < validation["ds"].min()
    assert train.iloc[-1]["y"] == 69
    assert validation.iloc[0]["y"] == 70


def test_split_time_series_rejects_insufficient_data():
    time_series = pd.DataFrame(
        {
            "ds": pd.date_range(start="2026-01-01", periods=40, freq="D"),
            "y": range(40),
        }
    )

    with pytest.raises(ValueError, match="yetersiz veri"):
        split_time_series(time_series)


def test_calculate_mape_returns_percentage():
    assert calculate_mape([100, 200], [90, 220]) == pytest.approx(10.0)


def test_calculate_mape_ignores_zero_actual_values():
    assert calculate_mape([0, 100], [50, 110]) == pytest.approx(10.0)


def test_calculate_mape_rejects_different_shapes():
    with pytest.raises(ValueError, match="boyutları aynı"):
        calculate_mape(y_true=[100, 200], y_pred=[100])


def test_forecast_config_rejects_invalid_days():
    with pytest.raises(ValueError, match="forecast_days"):
        ForecastConfig(forecast_days=0)


def test_create_future_dates_starts_after_last_date():
    time_series = build_sample_time_series(periods=100)
    future_dates = create_future_dates(
        time_series,
        config=ForecastConfig(forecast_days=30),
    )

    assert len(future_dates) == 30
    assert future_dates[0] == pd.Timestamp("2026-04-11")
    assert future_dates[-1] == pd.Timestamp("2026-05-10")


def test_forecast_prophet_produces_requested_predictions():
    time_series = build_sample_time_series(periods=100)
    future_dates = create_future_dates(
        time_series,
        config=ForecastConfig(forecast_days=7),
    )

    result = forecast_prophet(
        train=time_series,
        prediction_dates=future_dates,
    )

    assert list(result.columns) == ["ds", "yhat"]
    assert len(result) == 7
    assert result["yhat"].notna().all()
    assert np.isfinite(result["yhat"]).all()
    assert list(result["ds"]) == list(future_dates)


def test_forecast_arima_produces_requested_predictions():
    time_series = build_sample_time_series(periods=100)
    config = ForecastConfig(forecast_days=7, arima_order=(5, 1, 0))
    future_dates = create_future_dates(time_series, config=config)

    result = forecast_arima(
        train=time_series,
        prediction_dates=future_dates,
        config=config,
    )

    assert list(result.columns) == ["ds", "yhat"]
    assert len(result) == 7
    assert result["yhat"].notna().all()
    assert np.isfinite(result["yhat"]).all()
    assert list(result["ds"]) == list(future_dates)


def test_forecast_lightgbm_produces_recursive_predictions():
    time_series = build_sample_time_series(periods=100)
    config = ForecastConfig(forecast_days=7)
    future_dates = create_future_dates(time_series, config=config)

    result = forecast_lightgbm(
        train=time_series,
        prediction_dates=future_dates,
        config=config,
    )

    assert list(result.columns) == ["ds", "yhat"]
    assert len(result) == 7
    assert result["yhat"].notna().all()
    assert np.isfinite(result["yhat"]).all()
    assert (result["yhat"] >= 0).all()
    assert list(result["ds"]) == list(future_dates)


def test_forecast_lightgbm_rejects_short_history():
    time_series = build_sample_time_series(periods=30)
    future_dates = pd.date_range(start="2026-02-01", periods=7, freq="D")

    with pytest.raises(ValueError, match="yetersiz geçmiş"):
        forecast_lightgbm(
            train=time_series,
            prediction_dates=future_dates,
        )


def test_evaluate_forecast_returns_mape():
    validation = pd.DataFrame(
        {
            "ds": pd.date_range(start="2026-01-01", periods=2, freq="D"),
            "y": [100, 200],
        }
    )
    forecast = pd.DataFrame({"ds": validation["ds"], "yhat": [90, 220]})

    score = evaluate_forecast(validation=validation, forecast=forecast)

    assert score == pytest.approx(10.0)


def test_model_selector_compares_models_and_returns_future_forecast():
    time_series = build_sample_time_series(periods=140)
    source = time_series.rename(columns={"ds": "date", "y": "sales"})
    config = ForecastConfig(
        forecast_days=30,
        validation_days=30,
    )

    result = model_selector(
        df=source,
        date_column="date",
        target_column="sales",
        config=config,
    )

    assert isinstance(result, ForecastResult)
    assert result.selected_model in {"prophet", "arima", "lightgbm"}
    assert set(result.model_scores) == {"prophet", "arima", "lightgbm"}
    assert all(np.isfinite(score) for score in result.model_scores.values())
    assert result.failed_models == {}
    assert len(result.forecast) == 30
    assert list(result.forecast.columns) == ["ds", "yhat"]
    assert result.forecast.iloc[0]["ds"] == pd.Timestamp("2026-05-21")
    assert result.forecast["yhat"].notna().all()


def test_model_selector_continues_when_one_model_fails(monkeypatch):
    time_series = build_sample_time_series(periods=100)
    source = time_series.rename(columns={"ds": "date", "y": "sales"})

    def fake_forecast(model_name, train, prediction_dates, config):
        if model_name == "prophet":
            raise RuntimeError("Prophet test hatası")

        dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
        prediction_value = 140.0 if model_name == "arima" else 145.0
        return pd.DataFrame(
            {
                "ds": dates,
                "yhat": np.full(len(dates), prediction_value),
            }
        )

    monkeypatch.setattr(
        forecaster_module,
        "_forecast_with_model",
        fake_forecast,
    )

    result = model_selector(
        df=source,
        date_column="date",
        target_column="sales",
        config=ForecastConfig(forecast_days=7),
    )

    assert "prophet" not in result.model_scores
    assert result.failed_models == {"prophet": "Prophet test hatası"}
    assert result.selected_model in {"arima", "lightgbm"}
    assert len(result.forecast) == 7


def test_model_selector_raises_when_all_models_fail(monkeypatch):
    time_series = build_sample_time_series(periods=100)
    source = time_series.rename(columns={"ds": "date", "y": "sales"})

    def always_fail(model_name, train, prediction_dates, config):
        raise RuntimeError(f"{model_name} çalışmadı")

    monkeypatch.setattr(
        forecaster_module,
        "_forecast_with_model",
        always_fail,
    )

    with pytest.raises(RuntimeError, match="Hiçbir tahmin modeli"):
        model_selector(
            df=source,
            date_column="date",
            target_column="sales",
        )
