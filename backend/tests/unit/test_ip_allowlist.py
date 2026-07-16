"""IP allowlist helpers."""
from app.core.ip_allowlist import ip_allowed, client_ip_from_headers


def test_ip_allowed_cidr():
    assert ip_allowed("10.0.0.5", ["10.0.0.0/24"]) is True
    assert ip_allowed("10.0.1.5", ["10.0.0.0/24"]) is False


def test_client_ip_prefers_forwarded():
    assert (
        client_ip_from_headers(
            x_forwarded_for="1.2.3.4, 5.6.7.8",
            x_real_ip="9.9.9.9",
            peer="127.0.0.1",
        )
        == "1.2.3.4"
    )
