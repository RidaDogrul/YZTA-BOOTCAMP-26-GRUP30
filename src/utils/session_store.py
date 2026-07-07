"""
Session Store — In-Memory Oturum Yönetimi
------------------------------------------
Kullanıcının veri kaynağı bağlantılarını geçici olarak saklar.

Production'da Redis veya veritabanı kullanılmalı; bu MVP için basit
in-memory dict yeterli. FastAPI startup/shutdown event'leriyle
temizlik yapılabilir.

Kullanım:
    from src.utils.session_store import session_store
    
    # Yeni oturum aç
    session_id = session_store.create_session(connector, source_type="postgresql")
    
    # Oturumu al
    connector = session_store.get_connector(session_id)
    
    # Oturumu kapat
    session_store.close_session(session_id)
"""
from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from src.connectors.base import BaseConnector
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Session otomatik expire süresi (30 dakika)
DEFAULT_SESSION_TTL = timedelta(minutes=30)


class SessionStore:
    """
    Thread-safe in-memory session store.
    
    Her session:
    - session_id (str): Benzersiz oturum kimliği
    - connector (BaseConnector): Aktif DB konnektörü
    - source_type (str): "postgresql" | "mongodb" | "s3"
    - created_at (datetime): Oturum oluşturulma zamanı
    - last_accessed (datetime): Son erişim zamanı
    """

    def __init__(self, ttl: timedelta = DEFAULT_SESSION_TTL) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def create_session(
        self,
        connector: BaseConnector,
        source_type: str,
    ) -> str:
        """
        Yeni oturum oluşturur ve benzersiz session_id döndürür.
        
        Args:
            connector: Aktif DB konnektörü (PostgresConnector, MongoConnector, vb.)
            source_type: "postgresql" | "mongodb" | "s3"
        
        Returns:
            session_id: Frontend'in kullanacağı oturum kimliği
        """
        session_id = f"sess_{secrets.token_urlsafe(16)}"
        now = datetime.now(timezone.utc)

        with self._lock:
            self._sessions[session_id] = {
                "connector": connector,
                "source_type": source_type,
                "created_at": now,
                "last_accessed": now,
            }

        logger.info(
            "Session oluşturuldu",
            extra={"session_id": session_id, "source_type": source_type},
        )
        return session_id

    def get_connector(self, session_id: str) -> BaseConnector | None:
        """
        Session ID'ye karşılık gelen konnektörü döndürür.
        
        Args:
            session_id: Frontend'den gelen oturum kimliği
        
        Returns:
            BaseConnector | None: Oturum varsa ve geçerliyse konnektör, yoksa None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                logger.warning("Session bulunamadı", extra={"session_id": session_id})
                return None

            # TTL kontrolü
            now = datetime.now(timezone.utc)
            if now - session["last_accessed"] > self._ttl:
                logger.info("Session süresi doldu", extra={"session_id": session_id})
                self._close_session_unsafe(session_id)
                return None

            # Last accessed güncelle
            session["last_accessed"] = now
            return session["connector"]

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """
        Session hakkında meta bilgi döndürür (connector hariç).
        
        Returns:
            {"source_type": str, "created_at": datetime, "last_accessed": datetime}
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            return {
                "source_type": session["source_type"],
                "created_at": session["created_at"],
                "last_accessed": session["last_accessed"],
            }

    def close_session(self, session_id: str) -> bool:
        """
        Oturumu kapatır ve konnektör bağlantısını temizler.
        
        Returns:
            bool: Oturum kapatıldıysa True, bulunamadıysa False
        """
        with self._lock:
            return self._close_session_unsafe(session_id)

    def _close_session_unsafe(self, session_id: str) -> bool:
        """Thread-unsafe close (lock içinden çağrılmalı)."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False

        # Konnektör bağlantısını kapat
        try:
            connector = session["connector"]
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
        """
        Süresi dolmuş tüm oturumları temizler.
        
        Returns:
            int: Temizlenen oturum sayısı
        """
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
        """
        Tüm aktif oturumların meta bilgisini listeler (debug için).
        
        Returns:
            List of {"session_id", "source_type", "created_at", "last_accessed"}
        """
        with self._lock:
            return [
                {
                    "session_id": sid,
                    "source_type": s["source_type"],
                    "created_at": s["created_at"],
                    "last_accessed": s["last_accessed"],
                }
                for sid, s in self._sessions.items()
            ]

    def clear_all(self) -> int:
        """
        Tüm oturumları kapatır (test veya shutdown için).
        
        Returns:
            int: Kapatılan oturum sayısı
        """
        with self._lock:
            session_ids = list(self._sessions.keys())
            for sid in session_ids:
                self._close_session_unsafe(sid)

        logger.info("Tüm oturumlar kapatıldı", extra={"count": len(session_ids)})
        return len(session_ids)


# Global singleton instance
session_store = SessionStore()
