import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from main import app
import src.api.v1.endpoints.beta as beta_endpoint
from src.api.middleware.auth import create_access_token
from src.utils.beta_store import (
    InMemoryBetaStore,
    InvitationRedeemError,
    beta_store,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_beta_store():
    beta_store.reset()
    yield
    beta_store.reset()


def auth_headers(
    user_id: str,
    *,
    role: str | None = None,
) -> dict[str, str]:
    claims = {"role": role} if role is not None else None
    token = create_access_token(user_id, extra_claims=claims)
    return {"Authorization": f"Bearer {token}"}


def create_invitation(
    *,
    partner_name: str = "Örnek Design Partner",
    max_uses: int = 1,
) -> dict:
    response = client.post(
        "/api/v1/beta/invitations",
        headers=auth_headers("admin-1", role="admin"),
        json={
            "partner_name": partner_name,
            "expires_in_days": 14,
            "max_uses": max_uses,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_invitation_requires_jwt() -> None:
    response = client.post(
        "/api/v1/beta/invitations",
        json={
            "partner_name": "Yetkisiz Firma",
            "expires_in_days": 14,
            "max_uses": 1,
        },
    )

    assert response.status_code == 401


def test_create_invitation_requires_admin_role() -> None:
    response = client.post(
        "/api/v1/beta/invitations",
        headers=auth_headers("user-1", role="analyst"),
        json={
            "partner_name": "Yetkisiz Firma",
            "expires_in_days": 14,
            "max_uses": 1,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Bu işlem için admin yetkisi gerekli."


def test_admin_creates_and_lists_invitation_without_exposing_code() -> None:
    created = create_invitation()
    raw_code = created["code"]

    assert raw_code.startswith("BETA-")
    assert created["status"] == "active"
    assert created["use_count"] == 0

    response = client.get(
        "/api/v1/beta/invitations",
        headers=auth_headers("admin-1", role="admin"),
    )

    assert response.status_code == 200
    data = response.json()
    serialized = json.dumps(data, ensure_ascii=False)

    assert data["total"] == 1
    assert data["invitations"][0]["invitation_id"] == created["invitation_id"]
    assert raw_code not in serialized
    assert "code_hash" not in serialized


def test_user_redeems_invitation_and_gets_active_access() -> None:
    invitation = create_invitation()
    user_headers = auth_headers("user-1")

    redeem_response = client.post(
        "/api/v1/beta/redeem",
        headers=user_headers,
        json={"code": invitation["code"]},
    )

    assert redeem_response.status_code == 200
    redeemed = redeem_response.json()
    assert redeemed["user_id"] == "user-1"
    assert redeemed["has_access"] is True
    assert redeemed["status"] == "active"
    assert redeemed["partner_name"] == "Örnek Design Partner"

    access_response = client.get(
        "/api/v1/beta/access",
        headers=user_headers,
    )

    assert access_response.status_code == 200
    assert access_response.json()["has_access"] is True
    assert beta_store.has_active_access("user-1") is True


def test_access_endpoint_requires_jwt() -> None:
    response = client.get("/api/v1/beta/access")

    assert response.status_code == 401


def test_user_without_invitation_has_no_access() -> None:
    response = client.get(
        "/api/v1/beta/access",
        headers=auth_headers("user-without-invite"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-without-invite",
        "has_access": False,
        "status": "none",
        "invitation_id": None,
        "partner_name": None,
        "granted_at": None,
        "revoked_at": None,
        "revoked_by": None,
    }


def test_invalid_invitation_code_is_rejected() -> None:
    response = client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-1"),
        json={"code": "BETA-invalid-code-that-does-not-exist"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Davet kodu geçersiz veya kullanılamıyor."


def test_revoked_invitation_cannot_be_redeemed() -> None:
    invitation = create_invitation()
    admin_headers = auth_headers("admin-1", role="admin")

    revoke_response = client.delete(
        f"/api/v1/beta/invitations/{invitation['invitation_id']}",
        headers=admin_headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"

    redeem_response = client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-1"),
        json={"code": invitation["code"]},
    )

    assert redeem_response.status_code == 400


def test_single_use_invitation_cannot_be_used_by_second_user() -> None:
    invitation = create_invitation(max_uses=1)

    first_response = client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-1"),
        json={"code": invitation["code"]},
    )
    second_response = client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-2"),
        json={"code": invitation["code"]},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_same_user_cannot_redeem_twice() -> None:
    invitation = create_invitation(max_uses=2)
    headers = auth_headers("user-1")

    first_response = client.post(
        "/api/v1/beta/redeem",
        headers=headers,
        json={"code": invitation["code"]},
    )
    second_response = client.post(
        "/api/v1/beta/redeem",
        headers=headers,
        json={"code": invitation["code"]},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_admin_lists_design_partners() -> None:
    invitation = create_invitation()
    client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-1"),
        json={"code": invitation["code"]},
    )

    response = client.get(
        "/api/v1/beta/partners",
        headers=auth_headers("admin-1", role="admin"),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["partners"][0]["user_id"] == "user-1"


def test_non_admin_cannot_list_design_partners() -> None:
    response = client.get(
        "/api/v1/beta/partners",
        headers=auth_headers("user-1"),
    )

    assert response.status_code == 403


def test_admin_revokes_design_partner_access() -> None:
    invitation = create_invitation()
    client.post(
        "/api/v1/beta/redeem",
        headers=auth_headers("user-1"),
        json={"code": invitation["code"]},
    )

    revoke_response = client.delete(
        "/api/v1/beta/partners/user-1",
        headers=auth_headers("admin-1", role="admin"),
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["has_access"] is False
    assert revoke_response.json()["status"] == "revoked"
    assert beta_store.has_active_access("user-1") is False

    access_response = client.get(
        "/api/v1/beta/access",
        headers=auth_headers("user-1"),
    )
    assert access_response.json()["status"] == "revoked"


@dataclass
class MutableClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value

    def advance(self, delta: timedelta) -> None:
        self.value += delta


def test_expired_invitation_is_rejected_by_store() -> None:
    clock = MutableClock(datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc))
    store = InMemoryBetaStore(clock=clock)
    created = store.create_invitation(
        partner_name="Süre Testi",
        created_by="admin-1",
        expires_in=timedelta(minutes=5),
    )
    clock.advance(timedelta(minutes=6))

    with pytest.raises(InvitationRedeemError, match="kullanılamıyor"):
        store.redeem_invitation(
            code=created.code,
            user_id="user-1",
        )

    assert created.invitation.status_at(store.now()) == "expired"


def test_raw_invitation_code_is_never_logged(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(
        beta_endpoint.logger,
        "info",
        lambda message, extra: captured.append(
            {
                "message": message,
                "extra": extra,
            }
        ),
    )

    created = create_invitation()
    serialized_logs = json.dumps(captured, ensure_ascii=False)

    assert created["code"] not in serialized_logs
    assert "code_hash" not in serialized_logs
