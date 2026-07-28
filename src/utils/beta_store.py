"""Kapalı beta davetleri ve Design Partner erişimi için in-memory store.

Bu modül Sprint 3 MVP'sinde process belleğini kullanır. Uygulama yeniden
başlatıldığında kayıtlar silinir ve birden fazla worker arasında paylaşılmaz.
Endpoint katmanı ``BetaStore`` protokolüne bağlı olduğu için daha sonra aynı
arayüzü uygulayan kalıcı bir PostgreSQL store ile değiştirilebilir.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import threading
from typing import Literal, Protocol, TypeAlias


InvitationStatus: TypeAlias = Literal["active", "expired", "exhausted", "revoked"]
AccessStatus: TypeAlias = Literal["active", "revoked"]
Clock: TypeAlias = Callable[[], datetime]


class BetaStoreError(Exception):
    """Beta store işlemlerinin ortak hata tabanı."""


class InvitationNotFoundError(BetaStoreError):
    """Admin işlemi için davet kaydı bulunamadığında oluşur."""


class InvitationRedeemError(BetaStoreError):
    """Davet kodu geçersiz, süresi dolmuş veya kullanılamaz olduğunda oluşur."""


class BetaAccessAlreadyExistsError(BetaStoreError):
    """Kullanıcı zaten erişim sahibiyse veya aynı daveti kullandıysa oluşur."""


class BetaAccessNotFoundError(BetaStoreError):
    """İptal edilecek Design Partner erişimi bulunamadığında oluşur."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} boş olamaz.")
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{field_name} kontrol karakteri içeremez.")
    return normalized


def _hash_invitation_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _new_invitation_id() -> str:
    return f"inv_{secrets.token_urlsafe(12)}"


def _new_invitation_code() -> str:
    return f"BETA-{secrets.token_urlsafe(24)}"


@dataclass(frozen=True)
class InvitationRecord:
    """Ham davet kodunu içermeyen güvenli davet kaydı."""

    invitation_id: str
    code_hash: str = field(repr=False)
    partner_name: str = ""
    created_by: str = ""
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime = field(default_factory=_utc_now)
    max_uses: int = 1
    redeemed_user_ids: frozenset[str] = field(
        default_factory=frozenset,
        repr=False,
    )
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    @property
    def use_count(self) -> int:
        return len(self.redeemed_user_ids)

    def status_at(self, now: datetime) -> InvitationStatus:
        if self.revoked_at is not None:
            return "revoked"
        if now >= self.expires_at:
            return "expired"
        if self.use_count >= self.max_uses:
            return "exhausted"
        return "active"


@dataclass(frozen=True)
class CreatedInvitation:
    """Yalnızca oluşturma anında ham kodu taşıyan sonuç."""

    invitation: InvitationRecord
    code: str = field(repr=False)


@dataclass(frozen=True)
class BetaAccessRecord:
    """Bir kullanıcının Design Partner erişim kaydı."""

    user_id: str
    invitation_id: str
    partner_name: str
    granted_at: datetime
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    @property
    def status(self) -> AccessStatus:
        return "revoked" if self.revoked_at is not None else "active"

    @property
    def active(self) -> bool:
        return self.revoked_at is None


class BetaStore(Protocol):
    """Endpoint katmanının kullandığı değiştirilebilir store sözleşmesi."""

    def now(self) -> datetime:
        ...

    def create_invitation(
        self,
        *,
        partner_name: str,
        created_by: str,
        expires_in: timedelta,
        max_uses: int = 1,
    ) -> CreatedInvitation:
        ...

    def list_invitations(self) -> tuple[InvitationRecord, ...]:
        ...

    def revoke_invitation(
        self,
        invitation_id: str,
        *,
        revoked_by: str,
    ) -> InvitationRecord:
        ...

    def redeem_invitation(
        self,
        *,
        code: str,
        user_id: str,
    ) -> BetaAccessRecord:
        ...

    def get_access(self, user_id: str) -> BetaAccessRecord | None:
        ...

    def has_active_access(self, user_id: str) -> bool:
        ...

    def list_access_records(
        self,
        *,
        include_revoked: bool = False,
    ) -> tuple[BetaAccessRecord, ...]:
        ...

    def revoke_access(
        self,
        user_id: str,
        *,
        revoked_by: str,
    ) -> BetaAccessRecord:
        ...

    def reset(self) -> None:
        ...


class InMemoryBetaStore:
    """Thread-safe, process içi kapalı beta store'u."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or _utc_now
        self._invitations: dict[str, InvitationRecord] = {}
        self._access_records: dict[str, BetaAccessRecord] = {}
        self._lock = threading.RLock()

    def now(self) -> datetime:
        current = self._clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("BetaStore clock timezone-aware datetime döndürmelidir.")
        return current.astimezone(timezone.utc)

    def create_invitation(
        self,
        *,
        partner_name: str,
        created_by: str,
        expires_in: timedelta,
        max_uses: int = 1,
    ) -> CreatedInvitation:
        normalized_partner = _normalize_required(partner_name, "partner_name")
        normalized_creator = _normalize_required(created_by, "created_by")

        if expires_in <= timedelta(0):
            raise ValueError("expires_in pozitif olmalıdır.")
        if isinstance(max_uses, bool) or not isinstance(max_uses, int):
            raise TypeError("max_uses bir tam sayı olmalıdır.")
        if max_uses < 1:
            raise ValueError("max_uses en az 1 olmalıdır.")

        now = self.now()
        code = _new_invitation_code()
        record = InvitationRecord(
            invitation_id=_new_invitation_id(),
            code_hash=_hash_invitation_code(code),
            partner_name=normalized_partner,
            created_by=normalized_creator,
            created_at=now,
            expires_at=now + expires_in,
            max_uses=max_uses,
        )

        with self._lock:
            self._invitations[record.invitation_id] = record

        return CreatedInvitation(invitation=record, code=code)

    def list_invitations(self) -> tuple[InvitationRecord, ...]:
        with self._lock:
            records = tuple(self._invitations.values())
        return tuple(
            sorted(
                records,
                key=lambda item: item.created_at,
                reverse=True,
            )
        )

    def revoke_invitation(
        self,
        invitation_id: str,
        *,
        revoked_by: str,
    ) -> InvitationRecord:
        normalized_id = _normalize_required(invitation_id, "invitation_id")
        normalized_admin = _normalize_required(revoked_by, "revoked_by")

        with self._lock:
            record = self._invitations.get(normalized_id)
            if record is None:
                raise InvitationNotFoundError("Davet kaydı bulunamadı.")
            if record.revoked_at is None:
                record = replace(
                    record,
                    revoked_at=self.now(),
                    revoked_by=normalized_admin,
                )
                self._invitations[normalized_id] = record
            return record

    def redeem_invitation(
        self,
        *,
        code: str,
        user_id: str,
    ) -> BetaAccessRecord:
        normalized_code = _normalize_required(code, "code")
        normalized_user_id = _normalize_required(user_id, "user_id")
        code_hash = _hash_invitation_code(normalized_code)

        with self._lock:
            invitation = self._find_invitation_by_hash_unsafe(code_hash)
            if invitation is None or invitation.status_at(self.now()) != "active":
                raise InvitationRedeemError(
                    "Davet kodu geçersiz veya kullanılamıyor."
                )

            current_access = self._access_records.get(normalized_user_id)
            if current_access is not None and current_access.active:
                raise BetaAccessAlreadyExistsError(
                    "Kullanıcının aktif beta erişimi zaten bulunuyor."
                )
            if normalized_user_id in invitation.redeemed_user_ids:
                raise BetaAccessAlreadyExistsError(
                    "Bu davet kodu kullanıcı tarafından daha önce kullanılmış."
                )

            updated_invitation = replace(
                invitation,
                redeemed_user_ids=invitation.redeemed_user_ids
                | frozenset({normalized_user_id}),
            )
            access = BetaAccessRecord(
                user_id=normalized_user_id,
                invitation_id=invitation.invitation_id,
                partner_name=invitation.partner_name,
                granted_at=self.now(),
            )

            self._invitations[invitation.invitation_id] = updated_invitation
            self._access_records[normalized_user_id] = access
            return access

    def get_access(self, user_id: str) -> BetaAccessRecord | None:
        normalized_user_id = _normalize_required(user_id, "user_id")
        with self._lock:
            return self._access_records.get(normalized_user_id)

    def has_active_access(self, user_id: str) -> bool:
        access = self.get_access(user_id)
        return access is not None and access.active

    def list_access_records(
        self,
        *,
        include_revoked: bool = False,
    ) -> tuple[BetaAccessRecord, ...]:
        with self._lock:
            records = tuple(self._access_records.values())

        filtered = (
            records
            if include_revoked
            else tuple(record for record in records if record.active)
        )
        return tuple(
            sorted(
                filtered,
                key=lambda item: item.granted_at,
                reverse=True,
            )
        )

    def revoke_access(
        self,
        user_id: str,
        *,
        revoked_by: str,
    ) -> BetaAccessRecord:
        normalized_user_id = _normalize_required(user_id, "user_id")
        normalized_admin = _normalize_required(revoked_by, "revoked_by")

        with self._lock:
            record = self._access_records.get(normalized_user_id)
            if record is None:
                raise BetaAccessNotFoundError("Beta erişim kaydı bulunamadı.")
            if record.revoked_at is None:
                record = replace(
                    record,
                    revoked_at=self.now(),
                    revoked_by=normalized_admin,
                )
                self._access_records[normalized_user_id] = record
            return record

    def reset(self) -> None:
        """Test ve demo amacıyla tüm process içi kayıtları temizler."""
        with self._lock:
            self._invitations.clear()
            self._access_records.clear()

    def _find_invitation_by_hash_unsafe(
        self,
        code_hash: str,
    ) -> InvitationRecord | None:
        for invitation in self._invitations.values():
            if hmac.compare_digest(invitation.code_hash, code_hash):
                return invitation
        return None


beta_store = InMemoryBetaStore()


def get_beta_store() -> BetaStore:
    """FastAPI dependency; ileride PostgresBetaStore döndürecek şekilde değişebilir."""
    return beta_store
