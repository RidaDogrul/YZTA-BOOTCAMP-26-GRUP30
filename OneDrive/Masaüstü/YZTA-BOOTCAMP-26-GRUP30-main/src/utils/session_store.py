"""
Session Store — In-Memory Oturum Yönetimi
------------------------------------------
Kullanıcının veri kaynağı bağlantılarını geçici olarak saklar.

Her session birden fazla kaynak (connector) barındırabilir — bu sayede
kullanıcı tek oturumda birden fazla veritabanına bağlanarak federated
sorgular çalıştırabilir.

Session yapısı:
    {
        "sources": [
            {
                "connector":   <BaseConnector>,
                "source_type": "postgresql",
                "alias":       "Ana DB",       # kullanıcı dostu ad
                "source_id":   "src_xxxx",     # benzersiz kaynak kimliği
            },
            ...
        ],
        "primary_source_id": "src_xxxx",   # ilk eklenen kaynak
        "created_at":  datetime,
        "last_accessed": datetime,
    }

Geriye dönük uyumluluk: get_connector() birincil kaynağı döndürür.
Çoklu kaynak için get_all_connectors() kullanılır.
"""
from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Session otomatik expire süresi (30 dakika)
DEFAULT_SESSION_TTL = timedelta(minutes=30)


def _new_source_id() -> str:
    return f"src_{secrets.token_urlsafe(8)}"


class SessionStore:
    """
    Thread-safe in-memory session store.

    Her session birden fazla veri kaynağı tutabilir (multi-source).
    Geriye dönük uyumluluk için get_connector() / get_session_info()
    API'si korunmuştur.
    """

    def __init__(self, ttl: timedelta = DEFAULT_SESSION_TTL) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    # ------------------------------------------------------------------
    # Oturum oluşturma / kapatma
    # ------------------------------------------------------------------
    def create_session(
        self,
        connector: object,
        source_type: str,
        alias: str | None = None,
    ) -> str:
        """
        Yeni oturum oluşturur, ilk kaynağı ekler ve session_id döndürür.

        Args:
            connector:   Aktif DB konnektörü
            source_type: "postgresql" | "mysql" | "mongodb" | "s3" | "snowflake"
            alias:       Kullanıcı dostu kaynak adı (verilmezse source_type kullanılır)

        Returns:
            session_id: Frontend'in kullanacağı oturum kimliği
        """
        session_id = f"sess_{secrets.token_urlsafe(16)}"
        source_id = _new_source_id()
        now = datetime.now(timezone.utc)

        source_entry: dict[str, Any] = {
            "connector": connector,
            "source_type": source_type,
            "alias": alias or source_type,
            "source_id": source_id,
        }

        with self._lock:
            self._sessions[session_id] = {
                "sources": [source_entry],
                "primary_source_id": source_id,
                "created_at": now,
                "last_accessed": now,
            }

        logger.info(
            "Session oluşturuldu",
            extra={"session_id": session_id, "source_type": source_type},
        )
        return session_id

    def add_source(
        self,
        session_id: str,
        connector: object,
        source_type: str,
        alias: str | None = None,
    ) -> str | None:
        """
        Mevcut bir session'a yeni veri kaynağı ekler.

        Returns:
            source_id (str): Başarılı ise eklenen kaynağın ID'si, session yoksa None
        """
        source_id = _new_source_id()
        source_entry: dict[str, Any] = {
            "connector": connector,
            "source_type": source_type,
            "alias": alias or source_type,
            "source_id": source_id,
        }

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                logger.warning(
                    "add_source: Session bulunamadı",
                    extra={"session_id": session_id},
                )
                return None

            # TTL kontrolü
            now = datetime.now(timezone.utc)
            if now - session["last_accessed"] > self._ttl:
                logger.info(
                    "add_source: Session süresi dolmuş",
                    extra={"session_id": session_id},
                )
                self._close_session_unsafe(session_id)
                return None

            session["sources"].append(source_entry)
            session["last_accessed"] = now

        logger.info(
            "Kaynağa ek veri kaynağı eklendi",
            extra={
                "session_id": session_id,
                "source_id": source_id,
                "source_type": source_type,
            },
        )
        return source_id

    def remove_source(self, session_id: str, source_id: str) -> bool:
        """
        Session'dan belirtilen kaynağı kaldırır. Birincil kaynak kaldırılamaz.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            if session["primary_source_id"] == source_id:
                logger.warning(
                    "remove_source: Birincil kaynak kaldırılamaz",
                    extra={"session_id": session_id, "source_id": source_id},
                )
                return False

            before = len(session["sources"])
            session["sources"] = [
                s for s in session["sources"] if s["source_id"] != source_id
            ]
            return len(session["sources"]) < before

    # ------------------------------------------------------------------
    # Connector erişimi
    # ------------------------------------------------------------------
    def get_connector(self, session_id: str) -> object | None:
        """
        Geriye dönük uyumluluk — birincil (ilk) konnektörü döndürür.
        """
        sources = self._get_valid_sources(session_id)
        if sources is None:
            return None
        return sources[0]["connector"] if sources else None

    def get_all_connectors(
        self, session_id: str
    ) -> list[dict[str, Any]] | None:
        """
        Session'daki tüm kaynak bilgilerini döndürür.

        Returns:
            None       — session bulunamadı / süresi doldu
            list[dict] — [{"source_id", "source_type", "alias", "connector"}, ...]
        """
        sources = self._get_valid_sources(session_id)
        if sources is None:
            return None
        # connector nesnesini dışarı verirken kopyasını döndür
        return [
            {
                "source_id":   s["source_id"],
                "source_type": s["source_type"],
                "alias":       s["alias"],
                "connector":   s["connector"],
            }
            for s in sources
        ]

    def get_source_by_id(
        self, session_id: str, source_id: str
    ) -> dict[str, Any] | None:
        """Belirli bir source_id'ye ait kaynak girişini döndürür."""
        sources = self._get_valid_sources(session_id)
        if sources is None:
            return None
        for s in sources:
            if s["source_id"] == source_id:
                return {
                    "source_id":   s["source_id"],
                    "source_type": s["source_type"],
                    "alias":       s["alias"],
                    "connector":   s["connector"],
                }
        return None

    def _get_valid_sources(
        self, session_id: str
    ) -> list[dict[str, Any]] | None:
        """TTL doğrulaması yaparak sources listesini döndürür (lock içinde)."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                logger.warning(
                    "Session bulunamadı", extra={"session_id": session_id}
                )
                return None

            now = datetime.now(timezone.utc)
            if now - session["last_accessed"] > self._ttl:
                logger.info(
                    "Session süresi doldu", extra={"session_id": session_id}
                )
                self._close_session_unsafe(session_id)
                return None

            session["last_accessed"] = now
            return session["sources"]

    # ------------------------------------------------------------------
    # Oturum meta bilgisi
    # ------------------------------------------------------------------
    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """
        Session hakkında meta bilgi döndürür.

        Returns:
            {
                "source_type": str,          # birincil kaynak tipi (uyumluluk)
                "sources": [...],            # tüm kaynakların özeti
                "created_at": datetime,
                "last_accessed": datetime,
            }
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            primary_id = session["primary_source_id"]
            primary = next(
                (s for s in session["sources"] if s["source_id"] == primary_id),
                session["sources"][0] if session["sources"] else None,
            )
            sources_summary = [
                {
                    "source_id":   s["source_id"],
                    "source_type": s["source_type"],
                    "alias":       s["alias"],
                }
                for s in session["sources"]
            ]

            return {
                "source_type": primary["source_type"] if primary else "unknown",
                "sources": sources_summary,
                "created_at": session["created_at"],
                "last_accessed": session["last_accessed"],
            }

    def close_session(self, session_id: str) -> bool:
        """
        Oturumu kapatır ve tüm konnektör bağlantılarını temizler.
        """
        with self._lock:
            return self._close_session_unsafe(session_id)

    def _close_session_unsafe(self, session_id: str) -> bool:
        """Thread-unsafe close (lock içinden çağrılmalı)."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False

        for src in session.get("sources", []):
            try:
                connector = src["connector"]
                if hasattr(connector, "close"):
                    connector.close()
            except Exception as exc:
                logger.error(
                    "Konnektör kapatma hatası",
                    extra={"session_id": session_id, "error": str(exc)},
                )

        logger.info("Session kapatıldı", extra={"session_id": session_id})
        return True

    def cleanup_expired(self) -> int:
        """Süresi dolmuş tüm oturumları temizler."""
        now = datetime.now(timezone.utc)
        expired_ids: list[str] = []

        with self._lock:
            for sid, session in self._sessions.items():
                if now - session["last_accessed"] > self._ttl:
                    expired_ids.append(sid)

            for sid in expired_ids:
                self._close_session_unsafe(sid)

        if expired_ids:
            logger.info(
                "Süresi dolmuş oturumlar temizlendi",
                extra={"count": len(expired_ids)},
            )

        return len(expired_ids)

    def list_sessions(self) -> list[dict[str, Any]]:
        """Tüm aktif oturumların meta bilgisini listeler."""
        with self._lock:
            result: list[dict[str, Any]] = []
            for sid, s in self._sessions.items():
                primary_id = s["primary_source_id"]
                primary = next(
                    (src for src in s["sources"] if src["source_id"] == primary_id),
                    s["sources"][0] if s["sources"] else None,
                )
                result.append({
                    "session_id":   sid,
                    "source_type":  primary["source_type"] if primary else "unknown",
                    "source_count": len(s["sources"]),
                    "created_at":   s["created_at"],
                    "last_accessed": s["last_accessed"],
                })
            return result

    def clear_all(self) -> int:
        """Tüm oturumları kapatır (test veya shutdown için)."""
        with self._lock:
            session_ids = list(self._sessions.keys())
            for sid in session_ids:
                self._close_session_unsafe(sid)

        logger.info("Tüm oturumlar kapatıldı", extra={"count": len(session_ids)})
        return len(session_ids)


# Global singleton instance
session_store = SessionStore()
