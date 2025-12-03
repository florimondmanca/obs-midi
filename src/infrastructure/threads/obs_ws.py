import queue
import threading
import time
from typing import Callable

import websockets
import websockets.sync.client

from src.domain.command import (
    Command,
    ShowFilterCommand,
    SwitchSceneCommand,
)
from src.domain.obs import Event, Scene, SceneListChangedEvent
from src.infrastructure.adapters.obs_client import ObsClient


class ObsWebSocketController:
    def __init__(
        self,
        *,
        port: int,
        password: str,
        command_queue: queue.Queue[Command],
        on_event: Callable[[Event], None],
    ) -> None:
        self._port = port
        self._password = password
        self._command_queue = command_queue
        self._on_event = on_event

    def _run_request_sender(
        self,
        client: ObsClient,
        close_event: threading.Event,
    ) -> None:
        def log(*values: object) -> None:
            print("[ws][requests]", *values)

        try:
            log("Started")

            client.request_scene_list()

            while not close_event.is_set():
                try:
                    command = self._command_queue.get(timeout=1)
                except queue.Empty:
                    continue

                match command:
                    case SwitchSceneCommand():
                        scene = command.scene
                        log("Switch scene:", scene)
                        client.set_current_program_scene(scene)
                    case ShowFilterCommand():
                        source = command.source
                        filtername = command.filter
                        log("Show filter:", source, filtername)
                        client.enable_filter(source, filtername)

            log("Stopped")
        except Exception as exc:
            log("ERROR:", exc)
            raise

    def _run_event_receiver(
        self,
        client: ObsClient,
        close_event: threading.Event,
    ) -> None:
        def log(*values: object) -> None:
            print("[ws][events]", *values)

        try:
            log("Started")

            for event in client.iter_events():
                if close_event.is_set():
                    break

                if event is None:
                    continue

                # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#getscenelist
                if (
                    event["op"] == 7
                    and event["d"].get("requestType") == "GetSceneList"
                    and event["d"].get("requestStatus", {}).get("result")
                ):
                    self._on_event(
                        SceneListChangedEvent(
                            scenes=[
                                Scene(name=scene["sceneName"])
                                for scene in event["d"]["responseData"]["scenes"]
                            ]
                        )
                    )

            log("Stopped")
        except websockets.exceptions.ConnectionClosed:
            log("INFO: OBS was shut down, stopping...")
            close_event.set()
            return
        except Exception as exc:
            log("ERROR:", exc)
            raise

    def _run(self, close_event: threading.Event) -> None:
        def log(*values: object) -> None:
            print("[ws]", *values)

        threads = []
        sub_close_event = threading.Event()

        try:
            with websockets.sync.client.connect(f"ws://localhost:{self._port}") as ws:
                client = ObsClient(ws)
                client.authenticate(self._password)
                log("Connected")

                requests_t = threading.Thread(
                    target=self._run_request_sender, args=(client, sub_close_event)
                )
                requests_t.daemon = True
                requests_t.start()
                threads.append(requests_t)

                events_t = threading.Thread(
                    target=self._run_event_receiver,
                    args=(client, sub_close_event),
                )
                events_t.daemon = True
                events_t.start()
                threads.append(events_t)

                while all(t.is_alive() for t in threads):
                    time.sleep(0.2)

                    if close_event.is_set():
                        sub_close_event.set()
                        for t in threads:
                            t.join()

                close_event.set()

                for t in threads:
                    t.join()

            log("Stopped")

        except Exception as exc:
            log("ERROR:", exc)
            sub_close_event.set()

            for t in threads:
                t.join()

    def start_thread(
        self,
        close_event: threading.Event,
    ) -> threading.Thread:
        thread = threading.Thread(target=self._run, args=(close_event,))
        thread.daemon = True
        thread.start()
        return thread
