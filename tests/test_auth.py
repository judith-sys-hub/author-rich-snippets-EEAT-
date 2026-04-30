import json
import pytest


@pytest.fixture
def patched_session(tmp_path, monkeypatch):
    import scraper.auth as auth_mod
    monkeypatch.setattr(auth_mod, "SESSION_PATH", tmp_path / "session.json")
    return tmp_path / "session.json"


def test_load_session_returns_none_when_missing(patched_session):
    from scraper.auth import load_session
    assert load_session() is None


def test_save_and_load_roundtrip(patched_session):
    from scraper.auth import load_session, save_session
    cookies = [{"name": "session", "value": "abc123", "domain": ".kleinezeitung.at"}]
    save_session(cookies)
    assert load_session() == cookies
