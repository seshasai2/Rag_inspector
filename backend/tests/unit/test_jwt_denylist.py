"""Access JWT denylist helpers."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.core.jwt_denylist import (
    deny_access_jti,
    denylist_failopen_total,
    is_access_jti_denied,
    remaining_ttl_seconds,
    render_denylist_metrics_lines,
    reset_denylist_metrics_for_tests,
)


def test_remaining_ttl_seconds_positive():
    exp = datetime.now(timezone.utc).timestamp() + 120
    assert 100 <= remaining_ttl_seconds(exp) <= 120


def test_remaining_ttl_seconds_expired():
    exp = datetime.now(timezone.utc).timestamp() - 10
    assert remaining_ttl_seconds(exp) == 0
    assert remaining_ttl_seconds(None) == 0


def test_deny_and_check_with_fake_redis():
    store: dict[str, str] = {}

    client = MagicMock()
    client.set = MagicMock(side_effect=lambda k, v, ex=None: store.__setitem__(k, v))
    client.get = MagicMock(side_effect=lambda k: store.get(k))

    with patch("app.core.jwt_denylist._get_client", return_value=client):
        assert deny_access_jti("abc", 60) is True
        assert is_access_jti_denied("abc") is True
        assert is_access_jti_denied("other") is False


def test_denylist_fail_open_without_redis():
    reset_denylist_metrics_for_tests()
    with patch("app.core.jwt_denylist._get_client", return_value=None):
        assert deny_access_jti("abc", 60) is False
        assert is_access_jti_denied("abc") is False
    assert denylist_failopen_total() >= 2
    lines = "\n".join(render_denylist_metrics_lines())
    assert "raginspector_jwt_denylist_failopen_total" in lines
