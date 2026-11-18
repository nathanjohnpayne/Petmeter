"""The pull reply names the address the request arrived on.

The bar reaches the daemon through a name, and the router answers that name
with every address it has seen this Mac hold, dead ones included. The app pins
the address the daemon reports, so a press goes where the last poll got
through instead of to whatever the next DNS answer happens to be.
"""
import asyncio
import json
import socket

import pytest

from daemon.sinks import serve


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _get(port: int, target: str) -> dict:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET {target} HTTP/1.1\r\n\r\n".encode())
    await writer.drain()
    data = await reader.read()
    writer.close()
    return json.loads(data.split(b"\r\n\r\n", 1)[1])


@pytest.fixture(autouse=True)
def _stop():
    yield
    asyncio.run(serve.stop())


def test_the_reply_names_the_address_the_request_arrived_on():
    port = _free_port()

    async def scenario():
        assert await serve.start("127.0.0.1", port, log=lambda _: None) is True
        return await _get(port, serve.PATH)

    body = asyncio.run(scenario())
    assert body["host"] == f"http://127.0.0.1:{port}"
    assert "control" in body


def test_a_long_poll_answer_names_it_too():
    port = _free_port()

    async def scenario():
        assert await serve.start("127.0.0.1", port, log=lambda _: None) is True
        gen = serve.control.gen
        return await _get(port, f"{serve.PATH}?since={gen}&wait=50")

    body = asyncio.run(scenario())
    assert body["host"] == f"http://127.0.0.1:{port}"


def test_a_retried_press_is_applied_once():
    """The daemon applies a press before replying, so a lost reply makes the
    app retry a press that already landed. The id it reuses is how the retry
    is told apart from a second press."""
    c = serve.Control()
    c.press("pause", "1700000000000.1")
    c.press("pause", "1700000000000.1")       # the retry
    assert c.paused is True
    c.press("pause", "1700000000000.2")       # the next press
    assert c.paused is False


def test_a_press_without_an_id_is_always_applied():
    """An app installed before ids sends none; every press still counts."""
    c = serve.Control()
    c.press("pause")
    c.press("pause")
    assert c.paused is False
    c.set_cards(3)
    c.press("next")
    c.press("next")
    assert c.index == 2


def test_the_control_endpoint_drops_a_repeated_id():
    port = _free_port()

    async def scenario():
        assert await serve.start("127.0.0.1", port, log=lambda _: None) is True
        before = serve.control.paused
        first = await _get(port, f"{serve.CONTROL_PATH}?do=pause&id=t.1")
        again = await _get(port, f"{serve.CONTROL_PATH}?do=pause&id=t.1")
        return before, first, again

    before, first, again = asyncio.run(scenario())
    assert first["paused"] is (not before)
    assert again["paused"] is first["paused"]
    assert again["gen"] == first["gen"]


def test_a_retry_after_a_burst_of_presses_is_still_dropped():
    """A wheel spun fast sends many presses between a lost pause and its
    retry. Remembering only the last few ids would forget the pause's, and
    its retry would undo it."""
    c = serve.Control()
    c.set_cards(3)
    c.press("pause", "x.0")
    for i in range(1, 200):
        c.press("next", f"x.{i}")
    c.press("pause", "x.0")                   # the retry, after the burst
    assert c.paused is True


def test_press_ids_are_forgotten_after_the_window(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(serve.time, "monotonic", lambda: clock[0])
    c = serve.Control()
    c.press("pause", "y.1")
    clock[0] += serve.SEEN_S + 1
    c.press("pause", "y.2")                   # prunes y.1 on the way in
    assert "y.1" not in c._seen
    assert c.paused is False
