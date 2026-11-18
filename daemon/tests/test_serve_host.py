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
