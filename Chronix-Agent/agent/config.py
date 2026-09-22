"""
Configuration loading.

Precedence: environment variable CHRONIX_GEMINI_API_KEY overrides
config.json's gemini_api_key. This lets the API key be kept out of a
committed config.json entirely if desired (spec section 7/23).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

CONFIG_ENV_PATH = "CHRONIX_CONFIG_PATH"
DEFAULT_CONFIG_PATH = "config/config.json"
GEMINI_KEY_ENV = "CHRONIX_GEMINI_API_KEY"


@dataclass
class ChronixConfig:
    device_name: str = "Chronix-PC"
    server_port: int = 8765
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    auto_start: bool = False
    require_approval_for_medium: bool = False
    pairing_token: str = ""
    show_pairing_window: bool = True

    @classmethod
    def load(cls, path: str | None = None) -> "ChronixConfig":
        path = path or os.environ.get(CONFIG_ENV_PATH, DEFAULT_CONFIG_PATH)
        data: dict = {}
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        cfg = cls(
            device_name=data.get("device_name", cls.device_name),
            server_port=int(data.get("server_port", cls.server_port)),
            gemini_api_key=data.get("gemini_api_key", cls.gemini_api_key),
            gemini_model=data.get("gemini_model", cls.gemini_model),
            auto_start=bool(data.get("auto_start", cls.auto_start)),
            require_approval_for_medium=bool(
                data.get("require_approval_for_medium", cls.require_approval_for_medium)),
            pairing_token=data.get("pairing_token", cls.pairing_token),
            show_pairing_window=bool(data.get("show_pairing_window", cls.show_pairing_window)),
        )

        # Environment variable always wins, and is preferred so the key
        # never has to be committed to config.json at all.
        env_key = os.environ.get(GEMINI_KEY_ENV)
        if env_key:
            cfg.gemini_api_key = env_key

        return cfg

    def redacted_dict(self) -> dict:
        """Safe-to-log representation - never includes secrets (spec 22)."""
        d = self.__dict__.copy()
        d["gemini_api_key"] = "***set***" if self.gemini_api_key else "***unset***"
        d["pairing_token"] = "***set***" if self.pairing_token else "***unset***"
        return d
