"""
Chronix Agent entry point.

Run with:  python -m agent.main
Or via the packaged ChronixAgent.exe (see scripts/build_windows.py).
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from agent.config import ChronixConfig
from agent.discovery import DiscoveryBeacon
from agent.logger import setup_logging
from agent.server import run_server
from core.constants import PRODUCT_NAME, VERSION

log = logging.getLogger("chronix.main")


def _maybe_setup_auto_start(config: ChronixConfig) -> None:
    """First-run auto-start setup (spec section 24). Never loops or
    duplicates: enable_auto_start() itself checks is_configured() before
    creating anything, and this is only attempted when config.auto_start
    is true, which the user controls via config.json."""
    if not config.auto_start:
        return
    try:
        from agent.startup import enable_auto_start, AutoStartError
        enable_auto_start(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
    except AutoStartError as exc:
        log.warning("Could not configure auto-start: %s", exc)
    except Exception:  # noqa: BLE001 - auto-start must never block startup
        log.exception("Unexpected error while configuring auto-start (non-fatal).")


def _maybe_show_pairing_window(config: ChronixConfig, server) -> None:
    """Opens the pairing window unless the user has already paired a
    device (config.pairing_token is set) and hasn't asked to see it
    again. Controlled by config.show_pairing_window so headless/server
    deployments are not forced to open a GUI."""
    if not config.show_pairing_window:
        return
    try:
        from agent.pairing_ui import run_in_background
        run_in_background(
            generate_code=server.generate_pairing_code,
            device_name=config.device_name,
            port=config.server_port,
        )
    except Exception:  # noqa: BLE001 - pairing UI must never block startup
        log.exception("Could not open pairing window (non-fatal); "
                       "pairing can still be triggered another way.")


def main() -> int:
    setup_logging()
    log.info("%s %s starting...", PRODUCT_NAME, VERSION)

    config = ChronixConfig.load()
    log.info("Loaded config: %s", config.redacted_dict())

    _maybe_setup_auto_start(config)

    server = run_server(config)
    beacon = DiscoveryBeacon(config.device_name, config.server_port)
    beacon.start()

    _maybe_show_pairing_window(config, server)

    import threading
    stop_requested = threading.Event()

    def _handle_signal(signum, frame):
        log.info("Received signal %s, shutting down.", signum)
        stop_requested.set()

    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (AttributeError, ValueError):
        pass  # SIGTERM not available on this platform/thread

    try:
        while not stop_requested.is_set():
            server.approvals.sweep_expired()
            stop_requested.wait(5)
    finally:
        beacon.stop()
        server.shutdown()
        log.info("%s stopped.", PRODUCT_NAME)

    return 0


if __name__ == "__main__":
    sys.exit(main())
