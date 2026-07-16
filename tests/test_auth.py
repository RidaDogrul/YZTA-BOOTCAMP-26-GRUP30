from datetime import timedelta

import pytest
from fastapi import HTTPException

from src.api.middleware.auth import create_access_token, verify_access_token


def test_create_and_verify_access_token():
    token = create_access_token("user_123", extra_claims={"role": "analyst"})

    current_user = verify_access_token(token)

    assert current_user.user_id == "user_123"
    assert current_user.claims["role"] == "analyst"


def test_expired_token_is_rejected():
    token = create_access_token("user_123", expires_delta=timedelta(seconds=-1))

    with pytest.raises(HTTPException) as error:
        verify_access_token(token)

    assert error.value.status_code == 401
