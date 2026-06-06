from __future__ import annotations

import socket
import threading
from collections.abc import Callable
from types import TracebackType

_HOST = "127.0.0.1"
_PORT = 47320
_ACTIVATION_TOKEN = b"LEDGERA_ACTIVATE"


class SingleInstance:
    def __init__(self, server: socket.socket) -> None:
        self._server = server
        self._closed = threading.Event()
        self._callback_lock = threading.Lock()
        self._activation_callback: Callable[[], None] = lambda: None
        self._thread = threading.Thread(
            target=self._listen,
            name="ledgera-single-instance-activation",
            daemon=True,
        )
        self._thread.start()

    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        with self._callback_lock:
            self._activation_callback = callback

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        try:
            self._server.close()
        finally:
            self._thread.join(timeout=0.5)

    def __enter__(self) -> SingleInstance:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _listen(self) -> None:
        while not self._closed.is_set():
            try:
                client, _address = self._server.accept()
            except OSError:
                break
            with client:
                try:
                    payload = client.recv(len(_ACTIVATION_TOKEN))
                except OSError:
                    continue
            if payload == _ACTIVATION_TOKEN:
                self._activate()

    def _activate(self) -> None:
        with self._callback_lock:
            callback = self._activation_callback
        callback()


def acquire_single_instance(*, port: int = _PORT) -> SingleInstance | None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((_HOST, port))
        server.listen(1)
    except OSError:
        server.close()
        request_activation(port=port)
        return None
    return SingleInstance(server)


def request_activation(*, port: int = _PORT) -> None:
    try:
        with socket.create_connection((_HOST, port), timeout=0.25) as client:
            client.sendall(_ACTIVATION_TOKEN)
    except OSError:
        pass
