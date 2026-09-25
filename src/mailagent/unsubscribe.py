"""List-Unsubscribe handling (RFC 2369 and RFC 8058).

Three cases, in descending order of how automatable they are:

1. **One-click** (RFC 8058) — the sender advertises
   ``List-Unsubscribe-Post: List-Unsubscribe=One-Click`` and an HTTPS URL. A
   single POST completes it. Safe to automate.
2. **mailto:** — send an email to the given address. Safe to automate.
3. **Plain HTTPS link** — almost always lands on a page that needs a click.
   Not automatable; collect and hand to the human.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import requests

from .client import Gmail, Message

_TARGET = re.compile(r"<([^>]+)>")
_TIMEOUT = 20


@dataclass
class UnsubscribeTarget:
    message_id: str
    sender: str
    subject: str
    http_url: str | None = None
    mailto: str | None = None
    one_click: bool = False

    @property
    def method(self) -> str:
        if self.one_click and self.http_url:
            return "one-click"
        if self.mailto:
            return "mailto"
        if self.http_url:
            return "manual"
        return "none"

    @property
    def automatable(self) -> bool:
        return self.method in ("one-click", "mailto")

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "from": self.sender,
            "subject": self.subject,
            "method": self.method,
            "automatable": self.automatable,
            "http_url": self.http_url,
            "mailto": self.mailto,
        }


def parse(message: Message) -> UnsubscribeTarget | None:
    header = message.headers.get("list-unsubscribe")
    if not header:
        return None

    http_url = mailto = None
    for target in _TARGET.findall(header):
        target = target.strip()
        if target.lower().startswith("mailto:"):
            mailto = target
        elif target.lower().startswith(("http://", "https://")):
            http_url = target

    post = message.headers.get("list-unsubscribe-post", "")
    one_click = "one-click" in post.lower()

    return UnsubscribeTarget(
        message_id=message.id,
        sender=message.sender,
        subject=message.subject,
        http_url=http_url,
        mailto=mailto,
        one_click=one_click,
    )


def scan(gmail: Gmail, query: str = "", limit: int = 50) -> list[UnsubscribeTarget]:
    """Find messages offering an unsubscribe, newest first, one per sender."""
    seen: set[str] = set()
    out: list[UnsubscribeTarget] = []
    for msg in gmail.search(query, limit):
        target = parse(msg)
        if target is None or target.sender in seen:
            continue
        seen.add(target.sender)
        out.append(target)
    return out


def execute(gmail: Gmail, target: UnsubscribeTarget) -> str:
    """Perform the unsubscribe. Raises for the manual case."""
    if target.method == "one-click":
        resp = requests.post(
            target.http_url,
            data={"List-Unsubscribe": "One-Click"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return f"one-click POST returned {resp.status_code}"

    if target.method == "mailto":
        parsed = urlparse(target.mailto)
        params = parse_qs(parsed.query)
        gmail.send(
            to=parsed.path,
            subject=unquote(params.get("subject", ["unsubscribe"])[0]),
            body=unquote(params.get("body", ["unsubscribe"])[0]),
        )
        return f"unsubscribe email sent to {parsed.path}"

    raise ValueError(
        f"{target.sender} needs a manual click: {target.http_url}"
    )
