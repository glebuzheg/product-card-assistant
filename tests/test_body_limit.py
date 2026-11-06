import asyncio

import pytest

from product_cards.api import BodyLimit


def run_request(messages, *, read_again=False):
    received = []
    sent = []
    stream = iter(messages)

    async def receive():
        message = next(stream, None)
        assert message is not None, "Middleware read beyond the incoming stream"
        return message

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        received.append(await receive())
        if read_again:
            received.append(await receive())
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    asyncio.run(BodyLimit(app)({"type": "http"}, receive, send))
    return received, sent


@pytest.mark.parametrize("size,expected", [(65536, 204), (65537, 413)])
def test_body_size_boundary(size, expected):
    received, sent = run_request([{"type": "http.request", "body": b"x" * size}])
    assert sent[0]["status"] == expected
    assert bool(received) == (expected == 204)
    if expected == 413:
        import json

        detail = json.loads(sent[1]["body"])["detail"]
        assert isinstance(detail, str) and detail.strip()


def test_streaming_limit_counts_all_chunks():
    received, sent = run_request(
        [
            {"type": "http.request", "body": b"x" * 40000, "more_body": True},
            {"type": "http.request", "body": b"x" * 40000, "more_body": False},
        ]
    )
    assert not received
    assert sent[0]["status"] == 413


def test_streaming_body_is_reassembled_once_then_disconnect_is_forwarded():
    received, sent = run_request(
        [
            {"type": "http.request", "body": b"first", "more_body": True},
            {"type": "http.request", "body": b"second", "more_body": False},
            {"type": "http.disconnect"},
        ],
        read_again=True,
    )
    assert received == [
        {"type": "http.request", "body": b"firstsecond", "more_body": False},
        {"type": "http.disconnect"},
    ]
    assert sent[0]["status"] == 204


def test_missing_optional_body_is_empty():
    received, sent = run_request([{"type": "http.request"}])
    assert received[0]["body"] == b""
    assert sent[0]["status"] == 204


def test_disconnected_upload_is_not_forwarded():
    received, sent = run_request([{"type": "http.disconnect"}])
    assert received == []
    assert sent == []
