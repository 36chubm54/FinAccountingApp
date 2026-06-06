from __future__ import annotations

import socket
import threading

from app_single_instance import acquire_single_instance, request_activation


def test_second_acquire_returns_none_and_activates_first_instance() -> None:
    port = _free_port()
    activated = threading.Event()
    instance = acquire_single_instance(port=port)

    assert instance is not None
    with instance:
        instance.set_activation_callback(activated.set)

        assert acquire_single_instance(port=port) is None

        assert activated.wait(timeout=2)


def test_request_activation_notifies_running_instance() -> None:
    port = _free_port()
    activated = threading.Event()
    instance = acquire_single_instance(port=port)

    assert instance is not None
    with instance:
        instance.set_activation_callback(activated.set)

        request_activation(port=port)

        assert activated.wait(timeout=2)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])
