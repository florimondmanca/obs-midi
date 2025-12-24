import contextlib
import json
import queue
import threading
from typing import Callable, Iterator

import mido
import pytest
import websockets
from websockets.sync.connection import Connection
from websockets.sync.server import Server, serve

from obs_midi.core.main import run
from obs_midi.core.midi_in import MIDICallback
from obs_midi.core.obs_client import ObsDisconnect


@contextlib.contextmanager
def serve_ws(port: int, handler: Callable) -> Iterator[None]:
    q: queue.Queue[Server] = queue.Queue(maxsize=1)
    error_bucket: queue.Queue[Exception] = queue.Queue(maxsize=1)

    def _run_serve() -> None:
        with serve(handler, "", port) as server:
            q.put(server)
            try:
                server.serve_forever()
            except Exception as exc:
                error_bucket.put(exc)

    t = threading.Thread(target=_run_serve)
    t.start()
    server = q.get()
    try:
        yield
    finally:
        server.shutdown()
        t.join()
        if not error_bucket.empty():
            raise error_bucket.get()


def test_run_full() -> None:
    close_event = threading.Event()
    close_barrier = threading.Barrier(2)
    ready_event = threading.Event()
    server_error_bucket: queue.Queue[Exception] = queue.Queue(maxsize=1)

    @contextlib.contextmanager
    def open_dummy_input(callback: MIDICallback) -> Iterator[None]:
        def midi_stream() -> None:
            ready_event.wait()

            # NOTE: mido channels are 0-based

            # Non-registered message
            callback(mido.Message("control_change", channel=0, control=32, value=64))

            # First scene
            callback(mido.Message("control_change", channel=0, control=9, value=1))

            # Second scene
            callback(mido.Message("control_change", channel=1, control=19, value=64))

            # Third scene
            callback(mido.Message("control_change", channel=12, control=29, value=127))

            # Filter
            callback(mido.Message("control_change", channel=6, control=8, value=10))

            close_barrier.wait()
            close_event.set()

        threading.Thread(target=midi_stream, daemon=True).start()
        yield

    def handler(ws: Connection) -> None:
        try:
            # Authentication handshake
            ws.send(
                json.dumps(
                    {"d": {"authentication": {"salt": "test", "challenge": "test"}}}
                )
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

            scenes = [
                "Scene1 :: CC9#1@1",
                "Scene2 :: CC19#64@2",
                "Scene3 :: CC29#127@13",
            ]
            flash_source_name = "Flash Effect"
            flash_filter_name = "Flash :: CC08#010@07"  # Test leading zeroes

            ws.send(
                json.dumps(
                    {
                        "op": 7,
                        "d": {
                            "requestId": request_id,
                            "requestStatus": {"result": True},
                            "requestType": "GetSceneList",
                            "responseData": {
                                "scenes": [{"sceneName": scene} for scene in scenes]
                            },
                        },
                    }
                )
            )

            # Application asks for scene item list for each scene

            for i, scene in enumerate(scenes):
                msg = json.loads(ws.recv())
                assert msg["op"] == 6
                assert msg["d"]["requestType"] == "GetSceneItemList"
                request_id = msg["d"]["requestId"]
                assert msg["d"]["requestData"]["sceneName"] == scene

                ws.send(
                    json.dumps(
                        {
                            "op": 7,
                            "d": {
                                "requestId": request_id,
                                "requestStatus": {"result": True},
                                "requestType": "GetSceneItemList",
                                "responseData": {
                                    "sceneItems": [{"sourceName": "Flash Effect"}]
                                    if i == 0
                                    else []
                                },
                            },
                        }
                    )
                )

            # Application asks for source filter list for returned source
            msg = json.loads(ws.recv())
            assert msg["op"] == 6
            assert msg["d"]["requestType"] == "GetSourceFilterList"
            request_id = msg["d"]["requestId"]

            ws.send(
                json.dumps(
                    {
                        "op": 7,
                        "d": {
                            "requestId": request_id,
                            "requestStatus": {"result": True},
                            "requestType": "GetSourceFilterList",
                            "responseData": {
                                "filters": [
                                    {
                                        "sourceName": flash_source_name,
                                        "filterName": flash_filter_name,
                                    }
                                ]
                            },
                        },
                    }
                )
            )

            # MIDI message #1 requests switching to Scene1
            msg = json.loads(ws.recv())
            assert msg["op"] == 6
            assert msg["d"]["requestType"] == "SetCurrentProgramScene"
            assert msg["d"]["requestData"]["sceneName"] == scenes[0]

            # MIDI message #2 requests switching to Scene2
            msg = json.loads(ws.recv())
            assert msg["op"] == 6
            assert msg["d"]["requestType"] == "SetCurrentProgramScene"
            assert msg["d"]["requestData"]["sceneName"] == scenes[1]

            # MIDI message #3 requests switching to Scene3
            msg = json.loads(ws.recv())
            assert msg["op"] == 6
            assert msg["d"]["requestType"] == "SetCurrentProgramScene"
            assert msg["d"]["requestData"]["sceneName"] == scenes[2]

            # MIDI message #4 requests toggling flash filter
            msg = json.loads(ws.recv())
            assert msg["op"] == 6
            assert msg["d"]["requestType"] == "SetSourceFilterEnabled"
            assert msg["d"]["requestData"]["sourceName"] == flash_source_name
            assert msg["d"]["requestData"]["filterName"] == flash_filter_name
            assert msg["d"]["requestData"]["filterEnabled"] is True

            close_barrier.wait()
            close_event.wait()

            try:
                ws.recv()
            except websockets.ConnectionClosedOK:
                pass
        except Exception as exc:
            server_error_bucket.put(exc)

    obs_disconnect_event = threading.Event()
    obs_reconnect_event = threading.Event()

    with serve_ws(3456, handler):
        run(
            midi_input_opener=open_dummy_input,
            obs_port=3456,
            obs_password="test",
            on_ready=lambda: ready_event.set(),
            on_obs_disconnect=lambda: obs_disconnect_event.set(),
            on_obs_reconnect=lambda: obs_reconnect_event.set(),
            close_event=close_event,
        )

    assert ready_event.is_set()
    assert not obs_disconnect_event.is_set()
    assert not obs_reconnect_event.is_set()
    assert close_event.is_set()
    if not server_error_bucket.empty():
        raise server_error_bucket.get()


def test_run_midi_and_obs_startup_errors() -> None:
    close_event = threading.Event()

    @contextlib.contextmanager
    def open_error_input(callback: MIDICallback) -> Iterator[None]:
        raise RuntimeError("MIDI Error")
        yield

    ready_event = threading.Event()
    obs_disconnect_event = threading.Event()
    obs_reconnect_event = threading.Event()

    with pytest.raises(ExceptionGroup) as context:
        run(
            midi_input_opener=open_error_input,
            obs_port=3456,  # No server running
            obs_password="test",
            on_ready=lambda: ready_event.set(),
            on_obs_disconnect=lambda: obs_disconnect_event.set(),
            on_obs_reconnect=lambda: obs_reconnect_event.set(),
            close_event=close_event,
        )

    assert not ready_event.is_set()
    assert not obs_disconnect_event.is_set()
    assert not obs_reconnect_event.is_set()
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
        ws.close(websockets.CloseCode.INVALID_DATA)

    ready_event = threading.Event()
    obs_disconnect_event = threading.Event()
    obs_reconnect_event = threading.Event()

    with serve_ws(3456, handler):
        with pytest.raises(ObsDisconnect) as ctx:
            run(
                midi_input_opener=open_dummy_input,
                obs_port=3456,
                obs_password="test",
                on_ready=lambda: ready_event.set(),
                on_obs_disconnect=lambda: obs_disconnect_event.set(),
                on_obs_reconnect=lambda: obs_reconnect_event.set(),
                close_event=close_event,
            )

    assert not ready_event.is_set()
    assert not obs_disconnect_event.is_set()
    assert not obs_reconnect_event.is_set()
    assert close_event.is_set()
    assert ctx.value.code == websockets.CloseCode.INVALID_DATA


def test_run_obs_reconnect() -> None:
    obs_reconnect_event = threading.Event()
    close_event = threading.Event()
    close_barrier = threading.Barrier(2)
    server_error_bucket: queue.Queue[Exception] = queue.Queue(maxsize=1)

    @contextlib.contextmanager
    def open_dummy_input(callback: MIDICallback) -> Iterator[None]:
        def midi_stream() -> None:
            ready_event.wait()

            obs_reconnect_event.wait()

            # First scene
            callback(mido.Message("control_change", channel=0, control=9, value=1))

            close_barrier.wait()
            close_event.set()

        threading.Thread(target=midi_stream, daemon=True).start()
        yield

    handler_called = False

    def handler(ws: Connection) -> None:
        nonlocal handler_called
        scene = "Scene1 :: CC9#1@1"

        try:
            if not handler_called:
                handler_called = True

                # Authentication handshake
                ws.send(
                    json.dumps(
                        {"d": {"authentication": {"salt": "test", "challenge": "test"}}}
                    )
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
                                "responseData": {"scenes": [{"sceneName": scene}]},
                            },
                        }
                    )
                )

                # Application asks for scene item list in scene

                msg = json.loads(ws.recv())
                assert msg["op"] == 6
                assert msg["d"]["requestType"] == "GetSceneItemList"
                request_id = msg["d"]["requestId"]
                assert msg["d"]["requestData"]["sceneName"] == scene

                ws.send(
                    json.dumps(
                        {
                            "op": 7,
                            "d": {
                                "requestId": request_id,
                                "requestStatus": {"result": True},
                                "requestType": "GetSceneItemList",
                                "responseData": {"sceneItems": []},
                            },
                        }
                    )
                )

                # Disconnect early
                ws.close(websockets.CloseCode.INTERNAL_ERROR)
            else:
                # Authentication handshake
                ws.send(
                    json.dumps(
                        {"d": {"authentication": {"salt": "test", "challenge": "test"}}}
                    )
                )
                msg = json.loads(ws.recv())
                assert msg["op"] == 1
                assert msg["d"]["rpcVersion"] == 1
                assert msg["d"]["authentication"]
                ws.send(json.dumps({"d": {"msg": "ok"}}))

                # MIDI message requests switching to Scene1
                msg = json.loads(ws.recv())
                assert msg["op"] == 6
                assert msg["d"]["requestType"] == "SetCurrentProgramScene"
                assert msg["d"]["requestData"]["sceneName"] == scene

                close_barrier.wait()
                close_event.wait()

                try:
                    ws.recv()
                except websockets.ConnectionClosedOK:
                    pass
        except Exception as exc:
            server_error_bucket.put(exc)

    ready_event = threading.Event()
    obs_disconnect_event = threading.Event()

    def on_obs_reconnect() -> None:
        assert obs_disconnect_event.is_set()
        obs_reconnect_event.set()

    with serve_ws(3456, handler):
        run(
            midi_input_opener=open_dummy_input,
            obs_port=3456,
            obs_password="test",
            on_ready=lambda: ready_event.set(),
            on_obs_disconnect=lambda: obs_disconnect_event.set(),
            on_obs_reconnect=on_obs_reconnect,
            obs_reconnect_delay=0.2,
            close_event=close_event,
        )

    assert ready_event.is_set()
    assert handler_called
    assert obs_disconnect_event.is_set()
    assert obs_reconnect_event.is_set()
    assert close_event.is_set()
    if not server_error_bucket.empty():
        raise server_error_bucket.get()
