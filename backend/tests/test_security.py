from app.core.security import read_state, sign_state


def test_google_oauth_state_is_signed() -> None:
    state = "test-state"
    assert read_state(sign_state(state)) == state
    assert read_state("tampered") is None
