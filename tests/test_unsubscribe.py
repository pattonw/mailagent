from mailagent.client import Message
from mailagent.unsubscribe import parse


def _msg(**headers) -> Message:
    return Message(
        id="m1",
        thread_id="t1",
        headers={k.lower().replace("_", "-"): v for k, v in headers.items()},
    )


def test_no_header_returns_none():
    assert parse(_msg(subject="hi")) is None


def test_one_click_detected():
    t = parse(
        _msg(
            list_unsubscribe="<https://example.com/u?t=abc>",
            list_unsubscribe_post="List-Unsubscribe=One-Click",
        )
    )
    assert t.method == "one-click"
    assert t.automatable
    assert t.http_url == "https://example.com/u?t=abc"


def test_mailto_preferred_when_no_one_click():
    t = parse(
        _msg(list_unsubscribe="<mailto:stop@example.com?subject=unsub>, <https://example.com/u>")
    )
    assert t.method == "mailto"
    assert t.automatable
    assert t.mailto.startswith("mailto:stop@example.com")


def test_plain_link_is_manual():
    t = parse(_msg(list_unsubscribe="<https://example.com/u>"))
    assert t.method == "manual"
    assert not t.automatable
