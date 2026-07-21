from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Literal, TypeAlias

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA

from src.utils.logger import get_logger
from src.utils.metrics import measure_model_inference

ModelName: TypeAlias = Literal["prophet", "arima", "lightgbm"]
AggregationMethod: TypeAlias = Literal["sum", "mean"]

PredictionDates: TypeAlias = pd.Series | pd.DatetimeIndex | list[pd.Timestamp]
NumericValues: TypeAlias = pd.Series | np.ndarray | list[float]
IntervalPair: TypeAlias = tuple[NumericValues, NumericValues]

PREDICTION_INTERVAL_LEVELS: tuple[int, ...] = (80, 95)
_INTERVAL_QUANTILES: Mapping[int, tuple[float, float]] = {
    80: (0.10, 0.90),
    95: (0.025, 0.975),
}

logger = get_logger(__name__)


@dataclass(frozen=True)
class ForecastConfig:
    """Tahmin motorunun ortak ayarları."""

    forecast_days: int = 30
    validation_days: int = 30
    min_train_size: int = 45
    min_validation_size: int = 7
    frequency: str = "D"
    aggregation: AggregationMethod = "sum"
    arima_order: tuple[int, int, int] = (5, 1, 0)
    lightgbm_lags: tuple[int, ...] = (1, 7, 14, 30)
    random_state: int = 42
    clip_negative_predictions: bool = True
    include_prediction_intervals: bool = False
    prophet_uncertainty_samples: int = 1000

    def __post_init__(self) -> None:
        if self.forecast_days <= 0:
            raise ValueError("forecast_days pozitif bir sayı olmalıdır.")

        if self.validation_days <= 0:
            raise ValueError("validation_days pozitif bir sayı olmalıdır.")

        if self.min_train_size <= 0:
            raise ValueError("min_train_size pozitif bir sayı olmalıdır.")

        if self.min_validation_size <= 0:
            raise ValueError("min_validation_size pozitif bir sayı olmalıdır.")

        if self.aggregation not in {"sum", "mean"}:
            raise ValueError("aggregation yalnızca 'sum' veya 'mean' olabilir.")

        if not self.lightgbm_lags:
            raise ValueError("lightgbm_lags boş olamaz.")

        if any(lag <= 0 for lag in self.lightgbm_lags):
            raise ValueError("lightgbm_lags içindeki değerler pozitif olmalıdır.")

        if self.prophet_uncertainty_samples <= 0:
            raise ValueError("prophet_uncertainty_samples pozitif olmalıdır.")


@dataclass
class ForecastResult:
    """AutoML model seçiminin ve nihai tahminin sonucu."""

    selected_model: ModelName
    model_scores: dict[str, float]
    forecast: pd.DataFrame
    failed_models: dict[str, str] = field(default_factory=dict)


def prepare_time_series(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    config: ForecastConfig | None = None,
) -> pd.DataFrame:
    """Ham DataFrame'i standart ds/y zaman serisine dönüştürür."""
    config = config or ForecastConfig()

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df bir pandas DataFrame olmalıdır.")

    if df.empty:
        raise ValueError("Tahmin verisi boş olamaz.")

    missing_columns = [
        column
        for column in (date_column, target_column)
        if column not in df.columns
    ]

    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"Eksik DataFrame sütunları: {missing_text}")

    prepared = df[[date_column, target_column]].copy()
    prepared.columns = ["ds", "y"]

    prepared["ds"] = pd.to_datetime(
        prepared["ds"],
        errors="coerce",
        format="mixed",
    )
    prepared["y"] = pd.to_numeric(prepared["y"], errors="coerce")
    prepared = prepared.dropna(subset=["ds"])

    if prepared.empty:
        raise ValueError("Geçerli bir tarih değeri bulunamadı.")

    if prepared["y"].notna().sum() == 0:
        raise ValueError("Geçerli bir sayısal hedef değeri bulunamadı.")

    if config.aggregation == "sum":
        prepared = (
            prepared.groupby("ds", as_index=False)["y"]
            .sum(min_count=1)
            .sort_values("ds")
        )
    else:
        prepared = (
            prepared.groupby("ds", as_index=False)["y"]
            .mean()
            .sort_values("ds")
        )

    prepared = prepared.set_index("ds").asfreq(config.frequency).reset_index()
    prepared["y"] = prepared["y"].interpolate(
        method="linear",
        limit_direction="both",
    )

    if prepared["y"].isna().any():
        raise ValueError("Eksik hedef değerlerinin tamamı doldurulamadı.")

    return prepared.reset_index(drop=True)


def split_time_series(
    time_series: pd.DataFrame,
    config: ForecastConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Zaman serisini kronolojik eğitim ve doğrulama bölümlerine ayırır."""
    config = config or ForecastConfig()
    required_size = config.min_train_size + config.min_validation_size

    if len(time_series) < required_size:
        raise ValueError(
            "Model değerlendirmesi için yetersiz veri. "
            f"En az {required_size} kayıt gerekli, "
            f"{len(time_series)} kayıt bulundu."
        )

    available_validation_size = len(time_series) - config.min_train_size
    validation_size = min(config.validation_days, available_validation_size)

    if validation_size < config.min_validation_size:
        raise ValueError("MAPE hesaplamak için yeterli doğrulama verisi bulunamadı.")

    train = time_series.iloc[:-validation_size].copy()
    validation = time_series.iloc[-validation_size:].copy()

    return train.reset_index(drop=True), validation.reset_index(drop=True)


def calculate_mape(
    y_true: pd.Series | np.ndarray | list[float],
    y_pred: pd.Series | np.ndarray | list[float],
) -> float:
    """MAPE değerini yüzde olarak hesaplar; gerçek değeri sıfır olanları atlar."""
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)

    if actual.shape != predicted.shape:
        raise ValueError("Gerçek ve tahmin dizilerinin boyutları aynı olmalıdır.")

    valid_mask = (
        np.isfinite(actual)
        & np.isfinite(predicted)
        & (np.abs(actual) > np.finfo(float).eps)
    )

    if not valid_mask.any():
        raise ValueError("MAPE hesaplamak için sıfırdan farklı gerçek değer gerekli.")

    percentage_errors = np.abs(
        (actual[valid_mask] - predicted[valid_mask]) / actual[valid_mask]
    )
    return float(np.mean(percentage_errors) * 100)


def create_future_dates(
    time_series: pd.DataFrame,
    config: ForecastConfig | None = None,
) -> pd.DatetimeIndex:
    """Zaman serisinin son tarihinden sonraki tahmin tarihlerini üretir."""
    config = config or ForecastConfig()

    if time_series.empty:
        raise ValueError("Gelecek tarihler boş bir zaman serisinden üretilemez.")

    if "ds" not in time_series.columns:
        raise ValueError("Zaman serisinde 'ds' tarih sütunu bulunmalıdır.")

    last_date = pd.Timestamp(time_series["ds"].max())
    date_range = pd.date_range(
        start=last_date,
        periods=config.forecast_days + 1,
        freq=config.frequency,
    )
    return pd.DatetimeIndex(date_range[1:])


def _build_forecast_frame(
    prediction_dates: PredictionDates,
    predictions: NumericValues,
    prediction_intervals: Mapping[int, IntervalPair] | None = None,
) -> pd.DataFrame:
    """Model çıktısını ortak tahmin ve opsiyonel aralık formatına dönüştürür."""
    dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
    predicted_values = np.asarray(predictions, dtype=float).reshape(-1)

    if len(dates) != len(predicted_values):
        raise ValueError("Tahmin tarihleri ile tahmin değerlerinin sayısı eşleşmiyor.")

    if not np.isfinite(predicted_values).all():
        raise ValueError("Model sonlu olmayan bir tahmin değeri üretti.")

    forecast = pd.DataFrame({"ds": dates, "yhat": predicted_values})

    if prediction_intervals is None:
        return forecast

    missing_levels = [
        level
        for level in PREDICTION_INTERVAL_LEVELS
        if level not in prediction_intervals
    ]
    if missing_levels:
        raise ValueError(
            "Eksik tahmin aralığı seviyeleri: "
            + ", ".join(f"%{level}" for level in missing_levels)
        )

    for level in PREDICTION_INTERVAL_LEVELS:
        lower_values, upper_values = prediction_intervals[level]
        lower = np.asarray(lower_values, dtype=float).reshape(-1)
        upper = np.asarray(upper_values, dtype=float).reshape(-1)

        if len(lower) != len(dates) or len(upper) != len(dates):
            raise ValueError(
                f"%{level} tahmin aralığı ile tahmin tarihi sayısı eşleşmiyor."
            )

        if not np.isfinite(lower).all() or not np.isfinite(upper).all():
            raise ValueError(f"%{level} tahmin aralığı sonlu olmayan değer içeriyor.")

        # Quantile modellerinde nadiren görülebilen kesişmeleri güvenli biçimde düzelt.
        forecast[f"yhat_lower_{level}"] = np.minimum(lower, predicted_values)
        forecast[f"yhat_upper_{level}"] = np.maximum(upper, predicted_values)

    # %95 bandı %80 bandından daha dar olamaz.
    forecast["yhat_lower_95"] = np.minimum(
        forecast["yhat_lower_95"],
        forecast["yhat_lower_80"],
    )
    forecast["yhat_upper_95"] = np.maximum(
        forecast["yhat_upper_95"],
        forecast["yhat_upper_80"],
    )
    return forecast


def _intervals_from_samples(
    samples: np.ndarray,
    expected_length: int,
) -> dict[int, IntervalPair]:
    """Posterior tahmin örneklerinden %80 ve %95 aralıklarını hesaplar."""
    sample_matrix = np.asarray(samples, dtype=float)

    if sample_matrix.ndim != 2:
        raise ValueError("Prophet tahmin örnekleri iki boyutlu olmalıdır.")

    if sample_matrix.shape[0] != expected_length:
        if sample_matrix.shape[1] == expected_length:
            sample_matrix = sample_matrix.T
        else:
            raise ValueError("Prophet tahmin örneği sayısı tarihlerle eşleşmiyor.")

    if not np.isfinite(sample_matrix).all():
        raise ValueError("Prophet sonlu olmayan tahmin örnekleri üretti.")

    return {
        level: (
            np.quantile(sample_matrix, lower_quantile, axis=1),
            np.quantile(sample_matrix, upper_quantile, axis=1),
        )
        for level, (lower_quantile, upper_quantile) in _INTERVAL_QUANTILES.items()
    }


def _split_confidence_interval(
    values: pd.DataFrame | np.ndarray,
    expected_length: int,
    level: int,
) -> IntervalPair:
    """statsmodels güven aralığı çıktısını alt ve üst dizilere ayırır."""
    interval_array = np.asarray(values, dtype=float)
    if interval_array.shape != (expected_length, 2):
        raise ValueError(f"ARIMA %{level} tahmin aralığı beklenen biçimde değil.")

    return interval_array[:, 0], interval_array[:, 1]


def forecast_prophet(
    train: pd.DataFrame,
    prediction_dates: PredictionDates,
    config: ForecastConfig | None = None,
) -> pd.DataFrame:
    """Prophet modelini eğitir ve verilen tarihler için tahmin üretir."""
    config = config or ForecastConfig()

    if train.empty:
        raise ValueError("Prophet boş eğitim verisiyle çalıştırılamaz.")

    if not {"ds", "y"}.issubset(train.columns):
        raise ValueError("Prophet eğitim verisi 'ds' ve 'y' sütunlarını içermelidir.")

    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality="auto",
        daily_seasonality=False,
        uncertainty_samples=config.prophet_uncertainty_samples,
    )
    model.fit(train[["ds", "y"]].copy())

    future = pd.DataFrame({"ds": pd.to_datetime(prediction_dates)})
    prediction_result = model.predict(future)

    prediction_intervals: Mapping[int, IntervalPair] | None = None
    if config.include_prediction_intervals:
        predictive_samples = model.predictive_samples(future)
        if "yhat" not in predictive_samples:
            raise ValueError("Prophet tahmin örneklerinde 'yhat' bulunamadı.")
        prediction_intervals = _intervals_from_samples(
            samples=np.asarray(predictive_samples["yhat"], dtype=float),
            expected_length=len(future),
        )

    return _build_forecast_frame(
        prediction_dates=future["ds"],
        predictions=prediction_result["yhat"],
        prediction_intervals=prediction_intervals,
    )


def forecast_arima(
    train: pd.DataFrame,
    prediction_dates: PredictionDates,
    config: ForecastConfig | None = None,
) -> pd.DataFrame:
    """ARIMA modelini eğitir ve verilen tarihler için tahmin üretir."""
    config = config or ForecastConfig()

    if train.empty:
        raise ValueError("ARIMA boş eğitim verisiyle çalıştırılamaz.")

    if "y" not in train.columns:
        raise ValueError("ARIMA eğitim verisi 'y' sütununu içermelidir.")

    dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
    target_values = train["y"].astype(float).to_numpy()
    model = ARIMA(endog=target_values, order=config.arima_order)
    fitted_model = model.fit()
    forecast_result = fitted_model.get_forecast(steps=len(dates))
    predictions = np.asarray(forecast_result.predicted_mean, dtype=float)

    prediction_intervals: Mapping[int, IntervalPair] | None = None
    if config.include_prediction_intervals:
        prediction_intervals = {
            level: _split_confidence_interval(
                values=forecast_result.conf_int(alpha=1 - (level / 100)),
                expected_length=len(dates),
                level=level,
            )
            for level in PREDICTION_INTERVAL_LEVELS
        }

    return _build_forecast_frame(
        prediction_dates=dates,
        predictions=predictions,
        prediction_intervals=prediction_intervals,
    )


def _lightgbm_feature_columns(config: ForecastConfig) -> list[str]:
    """LightGBM eğitim ve tahmin aşamasında kullanılacak sütun sırasını döndürür."""
    calendar_columns = ["day_of_week", "day_of_month", "month"]
    lag_columns = [f"lag_{lag}" for lag in config.lightgbm_lags]
    rolling_columns = ["rolling_mean_7", "rolling_mean_30"]
    return calendar_columns + lag_columns + rolling_columns


def _minimum_lightgbm_history(config: ForecastConfig) -> int:
    """Lag ve hareketli ortalama özellikleri için gereken minimum geçmişi döndürür."""
    return max(30, max(config.lightgbm_lags))


def _build_lightgbm_training_frame(
    train: pd.DataFrame,
    config: ForecastConfig,
) -> pd.DataFrame:
    """Zaman serisini LightGBM'in kullanabileceği denetimli öğrenme tablosuna çevirir."""
    if not {"ds", "y"}.issubset(train.columns):
        raise ValueError("LightGBM eğitim verisi 'ds' ve 'y' sütunlarını içermelidir.")

    minimum_history = _minimum_lightgbm_history(config)
    if len(train) <= minimum_history:
        raise ValueError(
            "LightGBM için yetersiz geçmiş veri. "
            f"En az {minimum_history + 1} kayıt gereklidir."
        )

    feature_frame = train[["ds", "y"]].copy().sort_values("ds").reset_index(drop=True)
    dates = pd.to_datetime(feature_frame["ds"])

    feature_frame["day_of_week"] = dates.dt.dayofweek
    feature_frame["day_of_month"] = dates.dt.day
    feature_frame["month"] = dates.dt.month

    for lag in config.lightgbm_lags:
        feature_frame[f"lag_{lag}"] = feature_frame["y"].shift(lag)

    shifted_target = feature_frame["y"].shift(1)
    feature_frame["rolling_mean_7"] = shifted_target.rolling(window=7).mean()
    feature_frame["rolling_mean_30"] = shifted_target.rolling(window=30).mean()

    return feature_frame.dropna().reset_index(drop=True)


def _build_lightgbm_feature_row(
    history: list[float],
    prediction_date: pd.Timestamp,
    config: ForecastConfig,
) -> dict[str, float]:
    """Tek bir gelecek gün için LightGBM özelliklerini üretir."""
    minimum_history = _minimum_lightgbm_history(config)
    if len(history) < minimum_history:
        raise ValueError("LightGBM tahmini için yeterli geçmiş değer bulunamadı.")

    row: dict[str, float] = {
        "day_of_week": float(prediction_date.dayofweek),
        "day_of_month": float(prediction_date.day),
        "month": float(prediction_date.month),
    }

    for lag in config.lightgbm_lags:
        row[f"lag_{lag}"] = float(history[-lag])

    row["rolling_mean_7"] = float(np.mean(history[-7:]))
    row["rolling_mean_30"] = float(np.mean(history[-30:]))
    return row


def forecast_lightgbm(
    train: pd.DataFrame,
    prediction_dates: PredictionDates,
    config: ForecastConfig | None = None,
) -> pd.DataFrame:
    """LightGBM modelini eğitir ve recursive biçimde tahmin üretir."""
    config = config or ForecastConfig()

    if train.empty:
        raise ValueError("LightGBM boş eğitim verisiyle çalıştırılamaz.")

    dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
    training_frame = _build_lightgbm_training_frame(train, config)
    feature_columns = _lightgbm_feature_columns(config)

    model = LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=config.random_state,
        n_jobs=1,
        verbosity=-1,
    )
    model.fit(training_frame[feature_columns], training_frame["y"])

    quantile_models: dict[float, LGBMRegressor] = {}
    if config.include_prediction_intervals:
        quantiles = sorted(
            {
                quantile
                for pair in _INTERVAL_QUANTILES.values()
                for quantile in pair
            }
        )
        for quantile in quantiles:
            quantile_model = LGBMRegressor(
                objective="quantile",
                alpha=quantile,
                n_estimators=300,
                learning_rate=0.05,
                num_leaves=31,
                random_state=config.random_state,
                n_jobs=1,
                verbosity=-1,
            )
            quantile_model.fit(
                training_frame[feature_columns],
                training_frame["y"],
            )
            quantile_models[quantile] = quantile_model

    history = train.sort_values("ds")["y"].astype(float).tolist()
    predictions: list[float] = []
    quantile_predictions: dict[float, list[float]] = {
        quantile: [] for quantile in quantile_models
    }

    for prediction_date in dates:
        feature_row = _build_lightgbm_feature_row(
            history=history,
            prediction_date=pd.Timestamp(prediction_date),
            config=config,
        )
        feature_data = pd.DataFrame([feature_row], columns=feature_columns)
        prediction = float(model.predict(feature_data)[0])

        if config.clip_negative_predictions:
            prediction = max(0.0, prediction)

        predictions.append(prediction)

        for quantile, quantile_model in quantile_models.items():
            quantile_prediction = float(quantile_model.predict(feature_data)[0])
            if config.clip_negative_predictions:
                quantile_prediction = max(0.0, quantile_prediction)
            quantile_predictions[quantile].append(quantile_prediction)

        history.append(prediction)

    prediction_intervals: Mapping[int, IntervalPair] | None = None
    if config.include_prediction_intervals:
        prediction_intervals = {
            level: (
                quantile_predictions[lower_quantile],
                quantile_predictions[upper_quantile],
            )
            for level, (lower_quantile, upper_quantile) in _INTERVAL_QUANTILES.items()
        }

    return _build_forecast_frame(
        prediction_dates=dates,
        predictions=predictions,
        prediction_intervals=prediction_intervals,
    )


def _forecast_with_model(
    model_name: ModelName,
    train: pd.DataFrame,
    prediction_dates: PredictionDates,
    config: ForecastConfig,
) -> pd.DataFrame:
    """Model adına göre ilgili tahmin fonksiyonunu çalıştırır."""
    if model_name == "prophet":
        return forecast_prophet(
            train=train,
            prediction_dates=prediction_dates,
            config=config,
        )

    if model_name == "arima":
        return forecast_arima(
            train=train,
            prediction_dates=prediction_dates,
            config=config,
        )

    if model_name == "lightgbm":
        return forecast_lightgbm(
            train=train,
            prediction_dates=prediction_dates,
            config=config,
        )

    raise ValueError(f"Desteklenmeyen model: {model_name}")


def model_selector(
    df: pd.DataFrame,
    date_column: str,
    target_column: str,
    config: ForecastConfig | None = None,
) -> ForecastResult:
    """
    Prophet, ARIMA ve LightGBM modellerini aynı doğrulama dönemiyle karşılaştırır.

    En düşük MAPE değerine sahip modeli seçer, seçilen modeli bütün geçmiş
    veriyle yeniden eğitir ve gelecek için nihai tahmini üretir. Bir model hata
    verirse hata kaydedilir ve diğer modeller değerlendirilmeye devam edilir.
    """
    config = config or ForecastConfig()
    validation_config = replace(
        config,
        include_prediction_intervals=False,
    )
    time_series = prepare_time_series(
        df=df,
        date_column=date_column,
        target_column=target_column,
        config=config,
    )
    train, validation = split_time_series(time_series, config=config)

    model_scores: dict[str, float] = {}
    failed_models: dict[str, str] = {}
    model_names: tuple[ModelName, ...] = ("prophet", "arima", "lightgbm")

    for model_name in model_names:
        try:
            with measure_model_inference(
                 model_name=model_name,
                 phase="validation",
            ):
                 validation_forecast = _forecast_with_model(
                  model_name=model_name,
                  train=train,
                  prediction_dates=validation["ds"],
                  config=validation_config,
                )
            score = evaluate_forecast(
                validation=validation,
                forecast=validation_forecast,
            )
            model_scores[model_name] = score
            logger.info(
                "Tahmin modeli değerlendirildi",
                extra={"model": model_name, "mape": round(score, 4)},
            )
        except Exception as exc:
            failed_models[model_name] = str(exc)
            logger.error(
                "Tahmin modeli değerlendirilemedi",
                extra={"model": model_name, "error": str(exc)},
            )

    if not model_scores:
        failure_summary = "; ".join(
            f"{model}: {error}" for model, error in failed_models.items()
        )
        raise RuntimeError(
            "Hiçbir tahmin modeli başarıyla çalışmadı. "
            f"Hatalar: {failure_summary}"
        )

    selected_model = min(
        model_names,
        key=lambda name: model_scores.get(
            name,
            float("inf"),
        ),
    )
    future_dates = create_future_dates(time_series, config=config)

    try:
        with measure_model_inference(
             model_name=selected_model,
            phase="final_forecast",
        ):
            final_forecast = _forecast_with_model(
               model_name=selected_model,
               train=time_series,
               prediction_dates=future_dates,
               config=config,
            )
    except Exception as exc:
        raise RuntimeError(
            f"Seçilen {selected_model} modeli nihai tahmini üretemedi: {exc}"
        ) from exc

    logger.info(
        "En iyi tahmin modeli seçildi",
        extra={
            "selected_model": selected_model,
            "mape": round(model_scores[selected_model], 4),
            "forecast_days": config.forecast_days,
            "prediction_intervals": (
                list(PREDICTION_INTERVAL_LEVELS)
                if config.include_prediction_intervals
                else []
            ),
        },
    )

    return ForecastResult(
        selected_model=selected_model,
        model_scores=model_scores,
        forecast=final_forecast,
        failed_models=failed_models,
    )


def evaluate_forecast(
    validation: pd.DataFrame,
    forecast: pd.DataFrame,
) -> float:
    """Doğrulama verisi ile model tahminini karşılaştırıp MAPE döndürür."""
    if "y" not in validation.columns:
        raise ValueError("Doğrulama verisi 'y' sütununu içermelidir.")

    if "yhat" not in forecast.columns:
        raise ValueError("Tahmin verisi 'yhat' sütununu içermelidir.")

    if len(validation) != len(forecast):
        raise ValueError("Doğrulama ve tahmin kayıt sayıları eşleşmelidir.")

    return calculate_mape(
        y_true=validation["y"],
        y_pred=forecast["yhat"],
    )
