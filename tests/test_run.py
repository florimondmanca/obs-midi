import contextlib
import json
import queue
import threading
from typing import Callable, Iterator

from websockets.sync.connection import Connection
from websockets.sync.server import Server, serve

from obs_midi.core.main import run
from obs_midi.core.midi import MIDICallback


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

        # Finish early
        close_event.set()

    with serve_ws(4456, handler):
        run(
            midi_input_opener=open_dummy_input,
            obs_port=4456,
            obs_password="test",
            on_ready=lambda: None,
            on_obs_disconnect=lambda: None,
            on_obs_reconnect=lambda: None,
            close_event=close_event,
        )
