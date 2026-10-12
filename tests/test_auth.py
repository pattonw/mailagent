"""A revoked refresh token must not break the command that re-authorises."""

import pytest
from google.auth.exceptions import RefreshError

from mailagent import auth


class _DeadCreds:
    valid = False
    expired = True
    refresh_token = "x"

    def refresh(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")


def test_non_interactive_gives_an_actionable_message(monkeypatch, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}")
    monkeypatch.setattr(auth, "TOKEN_PATH", token)
    monkeypatch.setattr(
        auth.Credentials, "from_authorized_user_file",
        staticmethod(lambda *a, **k: _DeadCreds()),
    )
    with pytest.raises(auth.AuthError) as exc:
        auth.load_credentials(interactive=False)
    assert "re-authorise" in str(exc.value)
    assert "Publish app" in str(exc.value)


def test_interactive_discards_the_dead_token_instead_of_raising(monkeypatch, tmp_path):
    token = tmp_path / "token.json"
    token.write_text("{}")
    creds_path = tmp_path / "credentials.json"
    monkeypatch.setattr(auth, "TOKEN_PATH", token)
    monkeypatch.setattr(auth, "CREDENTIALS_PATH", creds_path)
    monkeypatch.setattr(
        auth.Credentials, "from_authorized_user_file",
        staticmethod(lambda *a, **k: _DeadCreds()),
    )
    # No credentials.json, so it should reach the flow and complain about that
    # rather than dying on the refresh.
    with pytest.raises(auth.AuthError) as exc:
        auth.load_credentials(interactive=True)
    assert "OAuth client file" in str(exc.value)
    assert not token.exists()        # dead token cleared
