"""
Federated Orchestrator — Çoklu Kaynak Paralel Sorgu (Task S3-Multi)
---------------------------------------------------------------------
Birden fazla veri kaynağına (PostgreSQL, MySQL, MongoDB, S3, Snowflake)
aynı anda bağlanır; her kaynaktan soru bazlı veri çeker, temizler ve
tek bir birleşik sonuç döndürür.

Akış:
    user_question + [connector_1, connector_2, ...] + source_table_map
            │
            ▼  (ThreadPoolExecutor — paralel)
    Orchestrator.run() × N  →  N adet OrchestratorResult
            │
            ▼
    Sonuçları etiketle (_source_alias kolonu ekle)
            │
            ▼
    pd.concat → birleşik DataFrame
            │
            ▼
    DataScientistAgent.run() → temizlenmiş DataFrame
            │
            ▼
    FederatedResult

Kullanım:
    from src.agents.federated_orchestrator import FederatedOrchestrator

    fed = FederatedOrchestrator(
        sources=[
            {"connector": pg_conn,    "source_type": "postgresql", "alias": "Satış DB",
             "source_id": "src_001", "tables": ["orders", "customers"]},
            {"connector": mysql_conn, "source_type": "mysql",      "alias": "Finans DB",
             "source_id": "src_002", "tables": ["invoices"]},
        ]
    )
    result = fed.run("Her iki kaynaktan aylık geliri karşılaştır")
    print(result.combined_df)
    print(result.per_source_results)
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.agents.data_scientist import DataScientistAgent
from src.agents.orchestrator import Orchestrator, OrchestratorResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

MAX_WORKERS   = 5    # Aynı anda çalışacak maksimum thread sayısı
DEFAULT_LIMIT = 1000  # Kaynak başına satır limiti


# ---------------------------------------------------------------------------
# Sonuç veri sınıfı
# ---------------------------------------------------------------------------
@dataclass
class PerSourceResult:
    """Tek bir kaynaktan gelen sorgu sonucu."""

    source_id:   str
    source_type: str
    alias:       str
    success:     bool
    df:          pd.DataFrame = field(default_factory=pd.DataFrame)
    query:       str = ""
    error:       str | None = None
    row_count:   int = 0


@dataclass
class FederatedResult:
    """FederatedOrchestrator.run() çağrısının birleşik sonucu."""

    question:       str
    per_source:     list[PerSourceResult] = field(default_factory=list)
    combined_df:    pd.DataFrame = field(default_factory=pd.DataFrame)
    cleaning_summary: str = ""
    cleaning_report:  dict = field(default_factory=dict)
    total_rows:     int = 0
    error:          str | None = None
    failed_sources: list[str] = field(default_factory=list)   # başarısız alias'lar

    @property
    def success(self) -> bool:
        """En az bir kaynak başarılıysa True."""
        return any(r.success for r in self.per_source)

    @property
    def partial(self) -> bool:
        """Bazı kaynaklar başarılı, bazıları başarısız ise True."""
        statuses = [r.success for r in self.per_source]
        return any(statuses) and not all(statuses)


# ---------------------------------------------------------------------------
# FederatedOrchestrator
# ---------------------------------------------------------------------------
class FederatedOrchestrator:
    """
    Birden fazla veri kaynağını paralel sorgulayan orchestrator.

    Args:
        sources: Her elemanı şu alanları içeren dict listesi:
            - connector   (object)      : Hazır konnektör nesnesi
            - source_type (str)         : "postgresql" | "mysql" | "mongodb" | "s3" | "snowflake"
            - alias       (str)         : Kullanıcı dostu kaynak adı
            - source_id   (str)         : Benzersiz kaynak kimliği
            - tables      (list[str])   : [OPSİYONEL] Sorgulanacak tablolar/koleksiyonlar.
                                          Boşsa kaynak kendi şemasını kullanır.
        data_scientist: Özel DataScientistAgent (verilmezse varsayılan).
        max_workers:    Paralel thread sayısı (varsayılan 5).
    """

    def __init__(
        self,
        sources: list[dict[str, Any]],
        data_scientist: DataScientistAgent | None = None,
        max_workers: int = MAX_WORKERS,
    ) -> None:
        if not sources:
            raise ValueError("En az bir kaynak gereklidir.")

        self._sources      = sources
        self._ds           = data_scientist or DataScientistAgent()
        self._max_workers  = max_workers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        user_question: str,
        collection: str | None = None,
    ) -> FederatedResult:
        """
        Tüm kaynaklara paralel sorgu çalıştırır ve sonuçları birleştirir.

        Args:
            user_question: Kullanıcının doğal dil sorusu.
            collection:    MongoDB kaynakları için koleksiyon adı (None → otomatik).

        Returns:
            FederatedResult — .combined_df, .per_source, .success
        """
        fed = FederatedResult(question=user_question)

        # ── Paralel veri çekme ───────────────────────────────────
        per_source_map: dict[str, OrchestratorResult] = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self._max_workers, len(self._sources))
        ) as executor:
            future_to_src = {
                executor.submit(
                    self._query_one_source,
                    src,
                    user_question,
                    collection,
                ): src
                for src in self._sources
            }

            for future in concurrent.futures.as_completed(future_to_src):
                src = future_to_src[future]
                alias = src.get("alias", src.get("source_type", "?"))
                try:
                    orch_result = future.result()
                    per_source_map[src["source_id"]] = orch_result
                except Exception as exc:
                    logger.error(
                        "Kaynak sorgu hatası (thread)",
                        extra={"alias": alias, "error": str(exc)},
                    )
                    per_source_map[src["source_id"]] = None  # type: ignore[assignment]

        # ── Sonuçları derle ──────────────────────────────────────
        dfs_to_concat: list[pd.DataFrame] = []
        queries: list[str] = []

        for src in self._sources:
            sid   = src["source_id"]
            alias = src.get("alias", src.get("source_type", "?"))
            stype = src.get("source_type", "unknown")
            orch  = per_source_map.get(sid)

            if orch is None or not orch.success:
                error_msg = (orch.error if orch else "Thread hatası")
                fed.per_source.append(
                    PerSourceResult(
                        source_id=sid,
                        source_type=stype,
                        alias=alias,
                        success=False,
                        error=error_msg,
                    )
                )
                fed.failed_sources.append(alias)
                logger.warning(
                    "Kaynak başarısız",
                    extra={"alias": alias, "error": error_msg},
                )
                continue

            # Başarılı kaynaktan DataFrame'i al
            src_df = _extract_combined_df(orch)

            if not src_df.empty:
                # Kaynağı etiketle
                src_df = src_df.copy()
                src_df["_source_alias"] = alias
                src_df["_source_type"]  = stype
                dfs_to_concat.append(src_df)

            fed.per_source.append(
                PerSourceResult(
                    source_id=sid,
                    source_type=stype,
                    alias=alias,
                    success=True,
                    df=src_df,
                    query=orch.query,
                    row_count=len(src_df),
                )
            )
            if orch.query:
                queries.append(f"[{alias}] {orch.query}")

        # Hiçbir kaynak başarılı değilse erken dön
        if not dfs_to_concat:
            fed.error = (
                "Hiçbir kaynaktan veri çekilemedi. "
                "Başarısız kaynaklar: " + ", ".join(fed.failed_sources or ["(bilinmiyor)"])
            )
            logger.error("Federated sorgu tamamen başarısız", extra={"error": fed.error})
            return fed

        # ── Birleştir ────────────────────────────────────────────
        try:
            combined = pd.concat(dfs_to_concat, ignore_index=True, sort=False)
        except Exception as exc:
            logger.error("DataFrame birleştirme hatası", extra={"error": str(exc)})
            fed.error = f"Veriler birleştirilemedi: {exc}"
            return fed

        # ── Veri temizleme ───────────────────────────────────────
        # _source_alias / _source_type meta sütunlarını ayır — temizlikte bozulmasın
        meta_cols = [c for c in ["_source_alias", "_source_type"] if c in combined.columns]
        meta_df   = combined[meta_cols].copy() if meta_cols else pd.DataFrame()
        clean_input = combined.drop(columns=meta_cols, errors="ignore")

        try:
            cleaning = self._ds.run(clean_input)
            cleaned  = cleaning.cleaned_df
            # Meta kolonları geri ekle (index uyumu garanti değil, reset gerek)
            if not meta_df.empty:
                cleaned = pd.concat(
                    [cleaned.reset_index(drop=True), meta_df.reset_index(drop=True)],
                    axis=1,
                )
            fed.combined_df      = cleaned
            fed.total_rows       = len(cleaned)
            fed.cleaning_summary = cleaning.summary
            fed.cleaning_report  = cleaning.report
        except Exception as exc:
            logger.warning("Temizleme hatası, ham veri kullanılıyor", extra={"error": str(exc)})
            fed.combined_df      = combined
            fed.total_rows       = len(combined)
            fed.cleaning_summary = f"Temizleme atlandı: {exc}"

        logger.info(
            "Federated sorgu tamamlandı",
            extra={
                "total_rows":      fed.total_rows,
                "sources_ok":      sum(1 for r in fed.per_source if r.success),
                "sources_failed":  len(fed.failed_sources),
            },
        )
        return fed

    # ------------------------------------------------------------------
    # Her kaynağı ayrı thread'de sorgula
    # ------------------------------------------------------------------
    def _query_one_source(
        self,
        src: dict[str, Any],
        question: str,
        collection: str | None,
    ) -> OrchestratorResult:
        """
        Tek bir kaynağa Orchestrator ile sorgu çalıştırır.

        Kaynak, seçili tablolarla kısıtlanmışsa soruya tablo adlarını ekleyerek
        LLM'in doğru tabloya yönelmesini sağlar.
        """
        connector   = src["connector"]
        alias       = src.get("alias", "")
        tables      = src.get("tables") or []      # kullanıcının seçtiği tablolar
        source_type = src.get("source_type", "")

        # Tablo seçimi varsa soruya bağlam ekle
        effective_question = question
        if tables:
            tbl_str = ", ".join(tables)
            effective_question = (
                f"{question}\n"
                f"[Yalnızca şu tablolar/koleksiyonlar kullanılacak: {tbl_str}]"
            )

        logger.info(
            "Kaynak sorgulanıyor",
            extra={"alias": alias, "source_type": source_type, "tables": tables},
        )

        orch = Orchestrator(connector=connector)

        # MongoDB için koleksiyon seçimi
        mongo_collection = collection
        if source_type == "mongodb" and tables:
            mongo_collection = tables[0]   # ilk seçilen koleksiyonu kullan

        return orch.run(effective_question, collection=mongo_collection)


# ---------------------------------------------------------------------------
# Yardımcı
# ---------------------------------------------------------------------------
def _extract_combined_df(result: OrchestratorResult) -> pd.DataFrame:
    """
    OrchestratorResult'tan tek bir DataFrame çıkarır.
    S3 modunda tablolar concat edilir; diğer modlarda cleaned_df kullanılır.
    """
    if result.source == "s3" and result.s3_tables:
        try:
            return pd.concat(
                list(result.s3_tables.values()), ignore_index=True, sort=False
            )
        except Exception:
            pass

    if not result.cleaned_df.empty:
        return result.cleaned_df

    return result.raw_df
