"""The pull endpoint survives a restart that races the old daemon for its port.

`launchctl kickstart -k` starts the new daemon while the old one is still
letting go of the socket. Binding once left the new daemon running for good
with no server, and the BUSY Bar read "The host is unreachable" until someone
restarted it a second time.
"""
import asyncio
import socket

import pytest

from daemon.sinks import serve


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _holder(port: int) -> socket.socket:
    """A listener on the port, the way the exiting daemon holds it.

    SO_REUSEADDR does not let a second socket bind over a live listener, so
    this is the same EADDRINUSE the real restart hits.
    """
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen()
    return s


async def _get(port: int) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(f"GET {serve.PATH} HTTP/1.1\r\n\r\n".encode())
    await writer.drain()
    data = await reader.read()
    writer.close()
    return data


@pytest.fixture(autouse=True)
def _fast_retry(monkeypatch):
    monkeypatch.setattr(serve, "BIND_RETRY_S", (0.05,))
    yield
    asyncio.run(serve.stop())


def test_a_port_still_held_by_the_old_daemon_is_taken_once_it_lets_go():
    port = _free_port()
    lines: list[str] = []

    async def scenario():
        held = _holder(port)
        try:
            assert await serve.start("127.0.0.1", port, log=lines.append) is True
            assert serve._server is None          # not yet: someone has it
            await asyncio.sleep(0.2)
            assert serve._server is None          # still waiting, not given up
        finally:
            held.close()
        for _ in range(40):
            if serve._server is not None:
                break
            await asyncio.sleep(0.05)
        assert serve._server is not None
        assert b"200 OK" in await _get(port)
        await serve.stop()

    asyncio.run(scenario())
    assert any("in use" in line for line in lines)
    assert lines[-1] == f"busybar serve: 127.0.0.1:{port}{serve.PATH}"


def test_an_address_this_host_does_not_have_still_fails_at_once():
    """The bar unplugged: the USB interface is gone, and waiting will not help."""
    lines: list[str] = []

    async def scenario():
        # TEST-NET-1, reserved for documentation; never assigned to this host.
        return await serve.start("192.0.2.1", _free_port(), log=lines.append)

    assert asyncio.run(scenario()) is False
    assert serve._retry is None
    assert "not listening" in lines[-1]


def test_stop_cancels_a_bind_still_waiting_for_its_port():
    port = _free_port()

    async def scenario():
        held = _holder(port)
        try:
            await serve.start("127.0.0.1", port, log=lambda _: None)
            assert serve._retry is not None
            await serve.stop()
            assert serve._retry is None
        finally:
            held.close()
        await asyncio.sleep(0.2)
        assert serve._server is None              # nothing bound behind our back

    asyncio.run(scenario())
