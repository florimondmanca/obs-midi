import contextlib
import json
import queue
import threading
from typing import Callable, Iterator

import pytest
from websockets import CloseCode
from websockets.sync.connection import Connection
from websockets.sync.server import Server, serve

from obs_midi.core.main import run
from obs_midi.core.midi import MIDICallback
from obs_midi.core.obs_client import ObsDisconnect


@contextlib.contextmanager
def serve_ws(port: int, handler: Callable) -> Iterator[None]:
    q: queue.Queue[Server] = queue.Queue(maxsize=1)

    def _run_serve() -> None:
        with serve(handler, "", port) as server:
            q.put(server)
            server.serve_forever()

    t = threading.Thread(target=_run_serve)
    t.start()
    server = q.get()
    try:
        yield
    finally:
        server.shutdown()
        t.join()


def test_run() -> None:
    close_event = threading.Event()

    @contextlib.contextmanager
    def open_dummy_input(callback: MIDICallback) -> Iterator[None]:
        yield

    def handler(ws: Connection) -> None:
        # Authentication handshake
        ws.send(
            json.dumps({"d": {"authentication": {"salt": "test", "challenge": "test"}}})
        )
        msg = json.loads(ws.recv())
        assert msg["op"] == 1
        assert msg["d"]["rpcVersion"] == 1
        assert msg["d"]["authentication"]
        ws.send(json.dumps({"d": {"msg": "ok"}}))

        # Application asks for scene list
        msg = json.loads(ws.recv())
        assert msg["op"] == 6
        assert msg["d"]["requestType"] == "GetSceneList"
        request_id = msg["d"]["requestId"]

        ws.send(
            json.dumps(
                {
                    "op": 7,
                    "d": {
                        "requestId": request_id,
                        "requestStatus": {"result": True},
                        "requestType": "GetSceneList",
                        "data": {"scenes": []},
                    },
                }
            )
        )

        close_event.wait()

    def on_ready() -> None:
        # Finish early
        close_event.set()

    with serve_ws(4456, handler):
        run(
            midi_input_opener=open_dummy_input,
            obs_port=4456,
            obs_password="test",
            on_ready=on_ready,
            on_obs_disconnect=lambda: None,
            on_obs_reconnect=lambda: None,
            close_event=close_event,
        )

    assert close_event.is_set()


def test_run_startup_error() -> None:
    close_event = threading.Event()

    @contextlib.contextmanager
    def open_error_input(callback: MIDICallback) -> Iterator[None]:
        raise RuntimeError("MIDI Error")
        yield

    ws_handler_called = False

    def handler(ws: Connection) -> None:
        nonlocal ws_handler_called
        ws_handler_called = True

    on_ready_called = False

    def on_ready() -> None:
        nonlocal on_ready_called
        on_ready_called = True

    with pytest.raises(ExceptionGroup) as context:
        run(
            midi_input_opener=open_error_input,
            obs_port=4456,  # No server here
            obs_password="test",
            on_ready=on_ready,
            on_obs_disconnect=lambda: None,
            on_obs_reconnect=lambda: None,
            close_event=close_event,
        )

    assert not ws_handler_called
    assert not on_ready_called
    assert close_event.is_set()
    assert {str(exc) for exc in context.value.exceptions} == {
        "MIDI Error",
        "[Errno 111] Connection refused",
    }


def test_run_obs_auth_error() -> None:
    close_event = threading.Event()

    @contextlib.contextmanager
    def open_dummy_input(callback: MIDICallback) -> Iterator[None]:
        yield

    def handler(ws: Connection) -> None:
        # Authentication handshake
        ws.send(
            json.dumps({"d": {"authentication": {"salt": "test", "challenge": "test"}}})
        )
        msg = json.loads(ws.recv())
        assert msg["d"]["authentication"]
        ws.close(CloseCode.INVALID_DATA)

    on_ready_called = False

    def on_ready() -> None:
        nonlocal on_ready_called
        on_ready_called = True

    on_obs_disconnect_called = False

    def on_obs_disconnect() -> None:
        nonlocal on_obs_disconnect_called
        on_obs_disconnect_called = True

    on_obs_reconnect_called = False

    def oon_obs_reconnect() -> None:
        nonlocal on_obs_reconnect_called
        on_obs_reconnect_called = True

    with serve_ws(4456, handler):
        with pytest.raises(ObsDisconnect) as ctx:
            run(
                midi_input_opener=open_dummy_input,
                obs_port=4456,  # No server here
                obs_password="test",
                on_ready=on_ready,
                on_obs_disconnect=on_obs_disconnect,
                on_obs_reconnect=oon_obs_reconnect,
                close_event=close_event,
            )

    assert not on_ready_called
    assert not on_obs_disconnect_called
    assert not on_obs_reconnect_called
    assert close_event.is_set()
    assert ctx.value.code == CloseCode.INVALID_DATA
