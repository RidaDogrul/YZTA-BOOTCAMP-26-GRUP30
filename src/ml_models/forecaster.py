from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA

from src.utils.logger import get_logger
from src.utils.metrics import measure_model_inference

ModelName = Literal["prophet", "arima", "lightgbm"]
AggregationMethod = Literal["sum", "mean"]

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
    prediction_dates: pd.Series | pd.DatetimeIndex | list[pd.Timestamp],
    predictions: pd.Series | np.ndarray | list[float],
) -> pd.DataFrame:
    """Model çıktısını ortak ds/yhat DataFrame formatına dönüştürür."""
    dates = pd.DatetimeIndex(pd.to_datetime(prediction_dates))
    predicted_values = np.asarray(predictions, dtype=float).reshape(-1)

    if len(dates) != len(predicted_values):
        raise ValueError("Tahmin tarihleri ile tahmin değerlerinin sayısı eşleşmiyor.")

    if not np.isfinite(predicted_values).all():
        raise ValueError("Model sonlu olmayan bir tahmin değeri üretti.")

    return pd.DataFrame({"ds": dates, "yhat": predicted_values})


def forecast_prophet(
    train: pd.DataFrame,
    prediction_dates: pd.Series | pd.DatetimeIndex | list[pd.Timestamp],
) -> pd.DataFrame:
    """Prophet modelini eğitir ve verilen tarihler için tahmin üretir."""
    if train.empty:
        raise ValueError("Prophet boş eğitim verisiyle çalıştırılamaz.")

    if not {"ds", "y"}.issubset(train.columns):
        raise ValueError("Prophet eğitim verisi 'ds' ve 'y' sütunlarını içermelidir.")

    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality="auto",
        daily_seasonality=False,
    )
    model.fit(train[["ds", "y"]].copy())

    future = pd.DataFrame({"ds": pd.to_datetime(prediction_dates)})
    prediction_result = model.predict(future)

    return _build_forecast_frame(
        prediction_dates=future["ds"],
        predictions=prediction_result["yhat"],
    )


def forecast_arima(
    train: pd.DataFrame,
    prediction_dates: pd.Series | pd.DatetimeIndex | list[pd.Timestamp],
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
    predictions = fitted_model.forecast(steps=len(dates))

    return _build_forecast_frame(
        prediction_dates=dates,
        predictions=predictions,
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
    prediction_dates: pd.Series | pd.DatetimeIndex | list[pd.Timestamp],
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

    history = train.sort_values("ds")["y"].astype(float).tolist()
    predictions: list[float] = []

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
        history.append(prediction)

    return _build_forecast_frame(
        prediction_dates=dates,
        predictions=predictions,
    )


def _forecast_with_model(
    model_name: ModelName,
    train: pd.DataFrame,
    prediction_dates: pd.Series | pd.DatetimeIndex | list[pd.Timestamp],
    config: ForecastConfig,
) -> pd.DataFrame:
    """Model adına göre ilgili tahmin fonksiyonunu çalıştırır."""
    if model_name == "prophet":
        return forecast_prophet(
            train=train,
            prediction_dates=prediction_dates,
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
                  config=config,
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
