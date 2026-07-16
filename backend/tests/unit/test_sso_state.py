"""OAuth CSRF state mint/consume."""
from app.core.sso_state import consume_oauth_state, mint_oauth_state


def test_mint_and_consume_oauth_state():
    state = mint_oauth_state("google")
    assert consume_oauth_state(state, expected_provider="google") is True
    # Replay rejected when Redis blacklist works; without Redis may allow once more.
    # Signature + provider checks still apply:
    assert consume_oauth_state("bogus", expected_provider="google") is False
    assert consume_oauth_state(state, expected_provider="microsoft") is False


def test_oauth_state_rejects_tamper():
    state = mint_oauth_state("google")
    bad = state[:-4] + "dead"
    assert consume_oauth_state(bad, expected_provider="google") is False
