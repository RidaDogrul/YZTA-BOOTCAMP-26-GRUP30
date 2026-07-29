"""Sprint 3 L2 kapalı beta daveti ve Design Partner erişim demosu."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from main import app
from src.api.middleware.auth import create_access_token
from src.utils.beta_store import beta_store


def _headers(
    user_id: str,
    *,
    role: str | None = None,
) -> dict[str, str]:
    claims = {"role": role} if role is not None else None
    token = create_access_token(user_id, extra_claims=claims)
    return {"Authorization": f"Bearer {token}"}


def _print_response(title: str, response) -> None:
    print(f"\n{title}")
    print(f"HTTP {response.status_code}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def main() -> None:
    client = TestClient(app)
    admin_headers = _headers("admin-demo", role="admin")
    user_headers = _headers("user-demo")
    beta_store.reset()

    try:
        create_response = client.post(
            "/api/v1/beta/invitations",
            headers=admin_headers,
            json={
                "partner_name": "Demo Perakende A.Ş.",
                "expires_in_days": 14,
                "max_uses": 1,
            },
        )
        _print_response("1. ADMIN DAVET OLUŞTURDU", create_response)
        invitation_code = create_response.json()["code"]

        list_response = client.get(
            "/api/v1/beta/invitations",
            headers=admin_headers,
        )
        _print_response(
            "2. ADMIN DAVETLERİ LİSTELEDİ (HAM KOD YOK)",
            list_response,
        )

        redeem_response = client.post(
            "/api/v1/beta/redeem",
            headers=user_headers,
            json={"code": invitation_code},
        )
        _print_response("3. KULLANICI DAVETİ KULLANDI", redeem_response)

        access_response = client.get(
            "/api/v1/beta/access",
            headers=user_headers,
        )
        _print_response("4. KULLANICI ERİŞİMİNİ KONTROL ETTİ", access_response)

        partner_response = client.get(
            "/api/v1/beta/partners",
            headers=admin_headers,
        )
        _print_response("5. ADMIN DESIGN PARTNERLARI LİSTELEDİ", partner_response)

        revoke_response = client.delete(
            "/api/v1/beta/partners/user-demo",
            headers=admin_headers,
        )
        _print_response("6. ADMIN ERİŞİMİ İPTAL ETTİ", revoke_response)

        final_access_response = client.get(
            "/api/v1/beta/access",
            headers=user_headers,
        )
        _print_response(
            "7. KULLANICI ERİŞİMİNİN KAPANDIĞINI GÖRDÜ",
            final_access_response,
        )
    finally:
        beta_store.reset()


if __name__ == "__main__":
    main()
