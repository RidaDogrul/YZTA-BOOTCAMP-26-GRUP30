"""Sprint 3 M4: %80 ve %95 tahmin aralığı demosu."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ml_models.forecaster import ForecastConfig, model_selector


def build_demo_data(periods: int = 180) -> pd.DataFrame:
    """Trend ve haftalık mevsimsellik içeren örnek satış verisi üretir."""
    day_numbers = np.arange(periods)
    trend = 1200 + (day_numbers * 3.2)
    weekly = np.sin(2 * np.pi * day_numbers / 7) * 90
    monthly = np.sin(2 * np.pi * day_numbers / 30) * 35

    return pd.DataFrame(
        {
            "date": pd.date_range(start="2026-01-01", periods=periods, freq="D"),
            "sales": trend + weekly + monthly,
        }
    )


def main() -> None:
    result = model_selector(
        df=build_demo_data(),
        date_column="date",
        target_column="sales",
        config=ForecastConfig(
            forecast_days=30,
            include_prediction_intervals=True,
        ),
    )

    print("MODEL MAPE SKORLARI")
    for model_name, score in sorted(result.model_scores.items(), key=lambda item: item[1]):
        print(f"- {model_name}: %{score:.4f}")

    print(f"\nSEÇİLEN MODEL: {result.selected_model}")
    print("\n30 GÜNLÜK TAHMİN VE GÜVEN BANTLARI (İLK 10 GÜN)")
    print(result.forecast.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
