from pathlib import Path
import sys

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml_models.forecaster import ForecastConfig, model_selector


def build_demo_sales_data(periods: int = 365) -> pd.DataFrame:
    """Trend, haftalık mevsimsellik ve gürültü içeren örnek satış verisi üretir."""
    random_generator = np.random.default_rng(42)
    day_numbers = np.arange(periods)

    trend = 1000 + (day_numbers * 1.8)
    weekly = np.sin(2 * np.pi * day_numbers / 7) * 120
    monthly = np.sin(2 * np.pi * day_numbers / 30) * 60
    noise = random_generator.normal(loc=0, scale=25, size=periods)
    sales = np.maximum(0, trend + weekly + monthly + noise)

    return pd.DataFrame(
        {
            "order_date": pd.date_range(
                start="2025-01-01",
                periods=periods,
                freq="D",
            ),
            "daily_sales": sales,
        }
    )


def main() -> None:
    sales_data = build_demo_sales_data()
    config = ForecastConfig(
        forecast_days=30,
        validation_days=30,
    )

    result = model_selector(
        df=sales_data,
        date_column="order_date",
        target_column="daily_sales",
        config=config,
    )

    print("\nMODEL MAPE SKORLARI")
    for model_name, score in sorted(
        result.model_scores.items(),
        key=lambda item: item[1],
    ):
        print(f"- {model_name}: %{score:.4f}")

    if result.failed_models:
        print("\nBAŞARISIZ MODELLER")
        for model_name, error in result.failed_models.items():
            print(f"- {model_name}: {error}")

    print(f"\nSEÇİLEN MODEL: {result.selected_model}")
    print("\n30 GÜNLÜK TAHMİN (İLK 10 GÜN)")
    print(result.forecast.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
