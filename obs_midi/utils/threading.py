import contextlib
import threading
import time
from typing import Callable, Iterator

ClosableThreadFactory = Callable[[threading.Event], threading.Thread]


class ThreadManager:
    def __init__(self, thread_factories: list[ClosableThreadFactory]) -> None:
        self._close_event = threading.Event()
        self._threads: list[threading.Thread] = [
            thread_factory(self._close_event) for thread_factory in thread_factories
        ]

    def start_all(self) -> None:
        for thread in self._threads:
            thread.start()

    def poll_all(self) -> None:
        while all(t.is_alive() for t in self._threads):
            time.sleep(0.2)

        self.close_all()

    def close_all(self) -> None:
        self._close_event.set()

        for thread in self._threads:
            thread.join()


@contextlib.contextmanager
def start_thread_manager(
    *thread_factories: ClosableThreadFactory,
) -> Iterator[ThreadManager]:
    thread_manager = ThreadManager(list(thread_factories))
    thread_manager.start_all()
    try:
        yield thread_manager
    finally:
        thread_manager.close_all()
