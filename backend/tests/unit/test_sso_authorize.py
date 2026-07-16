"""SSO authorize shape without credentials (Phase 10.13)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_google_authorize_without_creds():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/identity/sso/google/authorize")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "google"
    assert body["status"] == "ready_for_provider_credentials"
    assert "authorization_url_template" in body
