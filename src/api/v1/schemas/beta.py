"""Kapalı beta daveti ve Design Partner erişim API şemaları."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


InvitationStatus = Literal["active", "expired", "exhausted", "revoked"]
AccessStatus = Literal["none", "active", "revoked"]


class InvitationCreateRequest(BaseModel):
    """Admin tarafından oluşturulacak beta davetinin ayarları."""

    partner_name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Davetin ait olduğu Design Partner veya firma adı.",
        examples=["Örnek Perakende A.Ş."],
    )
    expires_in_days: int = Field(
        default=14,
        ge=1,
        le=365,
        description="Davetin geçerli kalacağı gün sayısı.",
    )
    max_uses: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Davet kodunun azami kullanım sayısı.",
    )

    @field_validator("partner_name")
    @classmethod
    def validate_partner_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("partner_name boş olamaz.")
        return normalized


class InvitationResponse(BaseModel):
    """Ham kodu veya kod hash'ini içermeyen güvenli davet görünümü."""

    invitation_id: str
    partner_name: str
    created_by: str
    created_at: datetime
    expires_at: datetime
    max_uses: int
    use_count: int
    status: InvitationStatus
    revoked_at: datetime | None = None
    revoked_by: str | None = None


class InvitationCreateResponse(InvitationResponse):
    """Ham davet kodunu yalnızca oluşturma anında döndüren yanıt."""

    code: str = Field(
        ...,
        description="Yalnızca bu yanıtta gösterilen davet kodu.",
    )


class InvitationListResponse(BaseModel):
    total: int
    invitations: list[InvitationResponse]


class InvitationRedeemRequest(BaseModel):
    code: str = Field(
        ...,
        min_length=16,
        max_length=256,
        description="Kullanıcıya iletilen kapalı beta davet kodu.",
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("code boş olamaz.")
        return normalized


class BetaAccessResponse(BaseModel):
    user_id: str
    has_access: bool
    status: AccessStatus
    invitation_id: str | None = None
    partner_name: str | None = None
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None


class BetaPartnerListResponse(BaseModel):
    total: int
    partners: list[BetaAccessResponse]
