"""
Data Scientist Agent (Agent 2) — Task S2-O2
--------------------------------------------------------
preprocessor.py'deki DataCleaningPipeline'ı Orchestrator pipeline'ına bağlayan
ajan katmanı. SQLExecutor Agent 1 için ne yapıyorsa, bu sınıf Agent 2 için onu
yapar: ham bir DataFrame alır, temizler, yapılandırılmış bir sonuç döndürür.

Neden ayrı bir sınıf?
  - Orchestrator temizlemenin detayını bilmesin; sadece "ajanı çağırsın".
  - Her çalıştırmada TAZE bir pipeline kurulur (fit durumu çağrılar arası sızmaz).
  - Hem metin özeti hem YAPISAL rapor döndürülür (Insight Generator için).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.ml_models.preprocessor import (
    DataCleaningPipeline,
    NullStrategy,
    OutlierMethod,
    OutlierAction,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CleaningResult:
    """Data Scientist ajanının çıktısı."""

    cleaned_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: str = ""                                    # insan-okur rapor metni
    report: dict[str, Any] = field(default_factory=dict) # yapısal rapor (JSON'a uygun)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class DataScientistAgent:
    """
    Agent 2: ham veriyi temizler (null doldurma + outlier işleme).
    DataCleaningPipeline'ı sarar; Orchestrator bunu çağırır.

    Args:
        null_strategy: Eksik değer doldurma yöntemi ("mean" | "median" | "interpolate").
        outlier_method: Outlier tespiti ("iqr" | "zscore").
        outlier_action: Outlier'a ne yapılacağı ("remove" | "clip" | "flag").
        columns: İşlenecek sütunlar (None ise tüm sayısal sütunlar).
    """

    def __init__(
        self,
        null_strategy: NullStrategy = "median",
        outlier_method: OutlierMethod = "iqr",
        outlier_action: OutlierAction = "clip",
        columns: list[str] | None = None,
    ) -> None:
        # Ayarları saklıyoruz; her run()'da bunlarla TAZE pipeline kuracağız.
        self._config: dict[str, Any] = {
            "null_strategy": null_strategy,
            "outlier_method": outlier_method,
            "outlier_action": outlier_action,
            "columns": columns,
        }

    def run(self, df: pd.DataFrame) -> CleaningResult:
        """Ham DataFrame'i temizler ve yapılandırılmış sonuç döndürür."""
        # Boş veri: temizlemeye gerek yok.
        if df is None or df.empty:
            return CleaningResult(
                cleaned_df=df if df is not None else pd.DataFrame(),
                summary="Veri boş; temizleme yapılmadı.",
                report={"note": "empty"},
            )

        logger.info("Agent 2 (Data Scientist) başlıyor", extra={"rows": len(df)})
        try:
            # Her çağrıda taze pipeline → fit durumu çağrılar arası karışmaz.
            pipeline = DataCleaningPipeline(**self._config)
            cleaned = pipeline.fit_transform(df)
        except Exception as exc:  
            logger.error("Agent 2 başarısız", extra={"error": str(exc)})
            return CleaningResult(
                cleaned_df=df,
                error=f"Veri temizleme hatası: {exc}",
            )

        # preprocessor'ın CleaningReport'unu JSON'a uygun bir dict'e çevir.
        r = pipeline.report_
        structured = {
            "initial_shape": list(r.initial_shape),
            "final_shape": list(r.final_shape),
            "nulls_before": r.nulls_before,
            "nulls_filled": r.nulls_filled,
            "outliers_detected": r.outliers_detected,
            "outliers_handled": r.outliers_handled,
        }

        logger.info("Agent 2 tamamlandı", extra={"final_rows": len(cleaned)})
        return CleaningResult(
            cleaned_df=cleaned,
            summary=r.summary(),
            report=structured,
        )


# --- Hızlı test ---  python -m src.agents.data_scientist
if __name__ == "__main__":
    # Gerçek DB gerekmez: elle küçük bir DataFrame kuruyoruz.
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "age": [34, 28, None, 45, 150],  # 1 null, 1 outlier
        }
    )
    agent = DataScientistAgent()
    result = agent.run(df)

    print("Başarılı:", result.success)
    print("\n--- Temizlenmiş veri ---")
    print(result.cleaned_df)
    print("\n--- Metin özeti ---")
    print(result.summary)
    print("\n--- Yapısal rapor ---")
    print(result.report)