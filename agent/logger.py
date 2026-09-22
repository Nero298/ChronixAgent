"""
Logging setup - rotating file handler so logs cannot grow indefinitely
(spec section 22). Never pass secrets (API keys, pairing tokens) into
log calls; use ChronixConfig.redacted_dict() when logging config.
"""
from __future__ import annotations

import logging
import logging.handlers
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "chronix-agent.log")
MAX_BYTES = 2 * 1024 * 1024  # 2 MB - deliberately small for low-end PCs
BACKUP_COUNT = 3


def setup_logging(level: int = logging.INFO) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger("chronix")
    root.setLevel(level)
    if root.handlers:
        return  # already configured (avoid duplicate handlers on reload)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)
