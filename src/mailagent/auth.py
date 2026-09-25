"""OAuth for the Gmail API.

Deliberately scoped below full mailbox access: there is no
``https://mail.google.com/`` here, so permanent deletion is impossible. The
worst a bug or a bad instruction can do is move mail to Trash, which Gmail
keeps for 30 days.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",  # label, archive, trash
    "https://www.googleapis.com/auth/gmail.send",
]

CONFIG_DIR = Path(
    os.environ.get("MAILAGENT_CONFIG_DIR", Path.home() / ".config" / "mailagent")
)
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
TOKEN_PATH = CONFIG_DIR / "token.json"


class AuthError(RuntimeError):
    pass


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)


def load_credentials(interactive: bool = False) -> Credentials:
    """Return usable credentials, refreshing or running the OAuth flow as needed."""
    creds: Credentials | None = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write_private(TOKEN_PATH, creds.to_json())
        return creds

    if not interactive:
        raise AuthError(
            "No valid credentials. Run `mailagent auth` to authorise."
        )

    if not CREDENTIALS_PATH.exists():
        raise AuthError(
            f"Missing OAuth client file at {CREDENTIALS_PATH}.\n"
            "Create a Google Cloud project, enable the Gmail API, make an OAuth "
            "client of type 'Desktop app', download the JSON, and save it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    _write_private(TOKEN_PATH, creds.to_json())
    return creds


def revoke() -> bool:
    """Delete the stored token. Returns True if a token was removed."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        return True
    return False
