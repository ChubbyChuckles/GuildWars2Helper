"""Interaction with arcdps-bhud to detect character select state."""

from __future__ import annotations

import socket
import threading
import time
from functools import cached_property
from typing import Optional

import psutil


class Client(threading.Thread):
    def __init__(self, gw2_pid: Optional[int] = None):
        threading.Thread.__init__(self, daemon=True)
        self._client_initialized = False
        self._gw2_pid = gw2_pid
        self._is_char_select = False

    def run(self) -> None:
        if self._gw2_port is None:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("localhost", self._gw2_port))

        while True:
            try:
                len_bytes = sock.recv(8)
                if not len_bytes:
                    break
                msg_len = int.from_bytes(len_bytes, "little")
                msg = sock.recv(msg_len)
                if msg and msg[0] == 1:
                    self._is_char_select = msg[1] == 0
                    if not self._client_initialized:
                        self._client_initialized = True
            except OSError:
                self._client_initialized = False
                return

    @cached_property
    def _gw2_port(self) -> Optional[int]:
        if self._gw2_pid is None and self._find_gw2_instance() is None:
            return None
        return self._gw2_pid & 0xFFFF | 1 << 14 | 1 << 15

    def _find_gw2_instance(self) -> Optional[int]:
        try:
            process = next(
                proc
                for proc in psutil.process_iter(attrs=["name", "pid"])
                if proc.info["name"].lower() == "gw2-64.exe"
            )
            self._gw2_pid = process.info["pid"]
        except StopIteration:
            return None
        return self._gw2_pid

    @property
    def is_initialized(self) -> bool:
        return self._client_initialized

    @property
    def is_in_char_select(self) -> bool:
        return self._is_char_select


def is_in_char_select_screen(timeout: float = 15.0) -> Optional[bool]:
    client = Client()
    client.start()
    waited = 0.0
    step = 0.25
    while not client.is_initialized and waited < timeout:
        time.sleep(step)
        waited += step
    if not client.is_initialized:
        return None
    return client.is_in_char_select
