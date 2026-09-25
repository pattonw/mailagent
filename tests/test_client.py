import base64

from mailagent.client import _extract_body, _parse


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_prefers_plain_text_over_html():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>html</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("plain")}},
        ],
    }
    assert _extract_body(payload) == "plain"


def test_falls_back_to_html():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [{"mimeType": "text/html", "body": {"data": _b64("<p>html</p>")}}],
    }
    assert _extract_body(payload) == "<p>html</p>"


def test_headers_lowercased_and_flags_parsed():
    raw = {
        "id": "abc",
        "threadId": "t",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "hello",
        "payload": {"headers": [{"name": "Subject", "value": "Hi"}]},
    }
    m = _parse(raw, with_body=False)
    assert m.subject == "Hi"
    assert m.is_unread and m.in_inbox
