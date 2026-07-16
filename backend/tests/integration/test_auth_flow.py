"""Integration: full auth register → login → me → refresh → logout flow."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_register_login_me_refresh_logout(client: AsyncClient):
    email = f"flow+{uuid.uuid4().hex}@example.com"
    password = "FlowPass123!"

    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Flow User", "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    user = reg.json()
    assert user["email"] == email.lower()
    assert "id" in user

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens.get("access_token")
    assert tokens.get("refresh_token")
    assert not tokens.get("mfa_required")

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email.lower()

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_tokens = refreshed.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Old refresh token should be revoked after rotation.
    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse.status_code == 401

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout.status_code == 200
    assert "message" in logout.json()

    after_logout = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_auth_login_rejects_bad_password(client: AsyncClient):
    email = f"badpw+{uuid.uuid4().hex}@example.com"
    password = "GoodPass123!"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Bad PW", "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPass123!"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_requires_bearer(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
