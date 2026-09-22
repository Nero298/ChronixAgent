"""
LAN discovery via UDP broadcast (spec section 16). No VPS, no relay -
Android listens on DISCOVERY_UDP_PORT for these beacons and then talks
directly to the advertised port over HTTP.
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import time

from core.constants import DISCOVERY_SERVICE_ID, DISCOVERY_UDP_PORT, VERSION

log = logging.getLogger("chronix.discovery")

BEACON_INTERVAL_SECONDS = 5


class DiscoveryBeacon:
    def __init__(self, device_name: str, server_port: int):
        self.device_name = device_name
        self.server_port = server_port
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _payload(self) -> bytes:
        return json.dumps({
            "service": DISCOVERY_SERVICE_ID,
            "version": VERSION,
            "port": self.server_port,
            "device_name": self.device_name,
        }).encode("utf-8")

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            while not self._stop.is_set():
                try:
                    sock.sendto(self._payload(), ("255.255.255.255", DISCOVERY_UDP_PORT))
                except OSError as exc:
                    log.debug("Discovery broadcast failed (non-fatal): %s", exc)
                self._stop.wait(BEACON_INTERVAL_SECONDS)
        finally:
            sock.close()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="chronix-discovery")
        self._thread.start()
        log.info("LAN discovery beacon started (broadcasting every %ds).", BEACON_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop.set()
