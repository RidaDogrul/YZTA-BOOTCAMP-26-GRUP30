from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

NullStrategy = Literal["mean", "median", "interpolate"]
OutlierMethod = Literal["iqr", "zscore"]
OutlierAction = Literal["remove", "clip", "flag"]


@dataclass
class CleaningReport:
    """Pipeline çalıştıktan sonra üretilen özet rapor."""

    initial_shape: tuple = field(default=(0, 0))
    final_shape: tuple = field(default=(0, 0))
    nulls_before: dict = field(default_factory=dict)
    nulls_filled: dict = field(default_factory=dict)
    outliers_detected: dict = field(default_factory=dict)
    outliers_handled: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "==== Veri Temizleme Raporu ====",
            f"Başlangıç boyutu : {self.initial_shape}",
            f"Bitiş boyutu     : {self.final_shape}",
            "",
            "-- Null Doldurma --",
        ]
        for col, cnt in self.nulls_before.items():
            filled = self.nulls_filled.get(col, 0)
            lines.append(f"  {col}: {cnt} null bulundu, {filled} dolduruldu")

        lines.append("")
        lines.append("-- Outlier Tespiti --")
        for col, cnt in self.outliers_detected.items():
            handled = self.outliers_handled.get(col, 0)
            lines.append(f"  {col}: {cnt} outlier bulundu, {handled} işlendi")

        return "\n".join(lines)


class DataCleaningPipeline:
    """
    Sayısal sütunlar üzerinde null doldurma ve outlier tespiti/işleme yapan
    basit, genişletilebilir bir pipeline.

    Parametreler
    ----------
    null_strategy : {"mean", "median", "interpolate"}
        Eksik değerlerin nasıl doldurulacağı.
    outlier_method : {"iqr", "zscore"}
        Outlier tespit yöntemi.
    outlier_action : {"remove", "clip", "flag"}
        Tespit edilen outlier'lara ne yapılacağı.
        - remove : satırı komple siler
        - clip   : sınır değerlere çeker (winsorize)
        - flag   : silmez, sadece `<col>_is_outlier` sütunu ekler
    iqr_multiplier : float
        IQR yönteminde çarpan (varsayılan 1.5).
    zscore_threshold : float
        Z-score yönteminde eşik değer (varsayılan 3.0).
    columns : list[str] | None
        İşlenecek sayısal sütunlar. None ise tüm numeric sütunlar otomatik seçilir.
    """

    def __init__(
        self,
        null_strategy: NullStrategy = "median",
        outlier_method: OutlierMethod = "iqr",
        outlier_action: OutlierAction = "clip",
        iqr_multiplier: float = 1.5,
        zscore_threshold: float = 3.0,
        columns: Optional[list[str]] = None,
    ):
        self.null_strategy = null_strategy
        self.outlier_method = outlier_method
        self.outlier_action = outlier_action
        self.iqr_multiplier = iqr_multiplier
        self.zscore_threshold = zscore_threshold
        self.columns = columns

        # fit sırasında öğrenilen istatistikler (transform'da tekrar kullanmak için)
        self._fill_values: dict[str, float] = {}
        self._bounds: dict[str, tuple[float, float]] = {}
        self._fitted = False

        self.report_ = CleaningReport()

    # ------------------------------------------------------------------ #
    # Yardımcı metodlar
    # ------------------------------------------------------------------ #
    def _get_target_columns(self, df: pd.DataFrame) -> list[str]:
        if self.columns is not None:
            return [c for c in self.columns if c in df.columns]
        return df.select_dtypes(include=[np.number]).columns.tolist()

    def _compute_iqr_bounds(self, series: pd.Series) -> tuple[float, float]:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - self.iqr_multiplier * iqr
        upper = q3 + self.iqr_multiplier * iqr
        return lower, upper

    def _compute_zscore_bounds(self, series: pd.Series) -> tuple[float, float]:
        mean = series.mean()
        std = series.std(ddof=0)
        if std == 0 or np.isnan(std):
            return series.min(), series.max()
        lower = mean - self.zscore_threshold * std
        upper = mean + self.zscore_threshold * std
        return lower, upper

    def _detect_outlier_mask(self, series: pd.Series, col: str) -> pd.Series:
        lower, upper = self._bounds[col]
        return (series < lower) | (series > upper)

    # ------------------------------------------------------------------ #
    # Fit: istatistikleri öğren
    # ------------------------------------------------------------------ #
    def fit(self, df: pd.DataFrame) -> "DataCleaningPipeline":
        target_cols = self._get_target_columns(df)
        self.report_.initial_shape = df.shape

        for col in target_cols:
            series = df[col]
            self.report_.nulls_before[col] = int(series.isna().sum())

            # Null doldurma değeri öğren (mean/median için)
            if self.null_strategy == "mean":
                self._fill_values[col] = series.mean()
            elif self.null_strategy == "median":
                self._fill_values[col] = series.median()
            # interpolate için sabit fill_value gerekmez

            # Outlier sınırlarını, null'lar geçici doldurulduktan sonraki
            # dağılıma göre öğren
            temp_filled = series.fillna(series.median())

            if self.outlier_method == "iqr":
                self._bounds[col] = self._compute_iqr_bounds(temp_filled)
            elif self.outlier_method == "zscore":
                self._bounds[col] = self._compute_zscore_bounds(temp_filled)

        self._fitted = True
        return self

    # ------------------------------------------------------------------ #
    # Transform: öğrenilen istatistiklerle veriyi temizle
    # ------------------------------------------------------------------ #
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Pipeline henüz fit edilmedi. Önce .fit() veya .fit_transform() çağırın.")

        df_out = df.copy()
        target_cols = self._get_target_columns(df_out)

        # 1) Null doldurma
        for col in target_cols:
            n_missing = int(df_out[col].isna().sum())
            if n_missing == 0:
                self.report_.nulls_filled[col] = 0
                continue

            if self.null_strategy in ("mean", "median"):
                df_out[col] = df_out[col].fillna(self._fill_values[col])
            elif self.null_strategy == "interpolate":
                df_out[col] = df_out[col].interpolate(method="linear", limit_direction="both")

            remaining = int(df_out[col].isna().sum())
            self.report_.nulls_filled[col] = n_missing - remaining

        # 2) Outlier tespiti ve işleme
        rows_to_drop = pd.Series(False, index=df_out.index)

        for col in target_cols:
            mask = self._detect_outlier_mask(df_out[col], col)
            n_outliers = int(mask.sum())
            self.report_.outliers_detected[col] = n_outliers

            if n_outliers == 0:
                self.report_.outliers_handled[col] = 0
                continue

            lower, upper = self._bounds[col]

            if self.outlier_action == "clip":
                df_out[col] = df_out[col].clip(lower=lower, upper=upper)
                self.report_.outliers_handled[col] = n_outliers
            elif self.outlier_action == "flag":
                df_out[f"{col}_is_outlier"] = mask
                self.report_.outliers_handled[col] = n_outliers
            elif self.outlier_action == "remove":
                rows_to_drop |= mask
                self.report_.outliers_handled[col] = n_outliers

        if self.outlier_action == "remove" and rows_to_drop.any():
            df_out = df_out.loc[~rows_to_drop]

        self.report_.final_shape = df_out.shape
        return df_out.reset_index(drop=True)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.transform(df)