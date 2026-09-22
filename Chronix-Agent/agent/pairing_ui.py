"""
Chronix Agent - pairing window.

A minimal always-on-top Tkinter window that shows the current pairing
code so the user can type it into the Android app. This is the piece
that actually prevents "same Wi-Fi = can control my PC": without a
successful pairing exchange (see agent/server.py._handle_pair), the
HTTP server rejects every authenticated endpoint (core/security is not
involved here - see ChronixRequestHandler._authenticated in server.py).

Deliberately built on tkinter (stdlib, ships with the standard Windows
Python installer) rather than a heavier GUI toolkit, to keep the
Windows 7 / 2 GB RAM footprint small and avoid adding a dependency.

This window is optional UI, not a background service: agent/main.py
runs headless by default; call show_pairing_window() from a menu/tray
action or a first-run flow when the user wants to pair a new phone.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from core.constants import PRODUCT_NAME, VERSION

log = logging.getLogger("chronix.pairing_ui")

# Colors matching the Android app's ChronixTheme (ui/theme/Color.kt) so
# the two surfaces feel like one product.
COLOR_BG = "#050C12"        # ChronixMidnight
COLOR_SURFACE = "#0B2434"   # ChronixDarkBlue
COLOR_GOLD = "#D4AF37"      # ChronixGold
COLOR_TEXT = "#F5F0E6"      # ChronixTextPrimary
COLOR_TEXT_DIM = "#A9B4BD"  # ChronixTextSecondary


def show_pairing_window(
    generate_code: Callable[[], str],
    device_name: str,
    port: int,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Opens a small always-on-top window showing the current pairing code.

    Runs its own Tkinter mainloop on the calling thread - call this from
    a dedicated thread (see run_in_background()) if the caller must not
    block, e.g. because agent/main.py's server loop is already running.

    generate_code: called once when the window opens, and again each
    time the user clicks "New code". Should call
    ChronixHTTPServer.generate_pairing_code() so the code the window
    displays is the same one server.py._handle_pair() checks against.
    """
    import tkinter as tk
    from tkinter import font as tkfont

    root = tk.Tk()
    root.title(f"{PRODUCT_NAME} - Pairing")
    root.configure(bg=COLOR_BG)
    root.resizable(False, False)
    root.attributes("-topmost", True)

    width, height = 340, 260
    root.geometry(f"{width}x{height}")

    heading_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
    code_font = tkfont.Font(family="Consolas", size=32, weight="bold")
    body_font = tkfont.Font(family="Segoe UI", size=9)
    small_font = tkfont.Font(family="Segoe UI", size=8)

    tk.Label(
        root, text=PRODUCT_NAME, font=heading_font, fg=COLOR_GOLD, bg=COLOR_BG,
    ).pack(pady=(16, 2))

    tk.Label(
        root, text=f"{device_name}  •  port {port}",
        font=small_font, fg=COLOR_TEXT_DIM, bg=COLOR_BG,
    ).pack()

    tk.Label(
        root, text="Enter this code in the Android app to pair:",
        font=body_font, fg=COLOR_TEXT, bg=COLOR_BG,
    ).pack(pady=(14, 4))

    code_frame = tk.Frame(root, bg=COLOR_SURFACE, highlightbackground=COLOR_GOLD,
                           highlightthickness=1)
    code_frame.pack(pady=4)

    code_var = tk.StringVar(value=generate_code())
    code_label = tk.Label(
        code_frame, textvariable=code_var, font=code_font,
        fg=COLOR_GOLD, bg=COLOR_SURFACE, padx=24, pady=10,
    )
    code_label.pack()

    status_var = tk.StringVar(value="Waiting for a device to pair...")
    tk.Label(
        root, textvariable=status_var, font=small_font, fg=COLOR_TEXT_DIM, bg=COLOR_BG,
    ).pack(pady=(10, 0))

    def _regenerate():
        code_var.set(generate_code())
        status_var.set("New code generated. Waiting for a device to pair...")
        log.info("Pairing code regenerated via UI.")

    button_frame = tk.Frame(root, bg=COLOR_BG)
    button_frame.pack(pady=14)

    new_code_btn = tk.Button(
        button_frame, text="New code", command=_regenerate,
        bg=COLOR_SURFACE, fg=COLOR_TEXT, activebackground=COLOR_GOLD,
        activeforeground=COLOR_BG, relief="flat", padx=14, pady=6,
        font=body_font, cursor="hand2",
    )
    new_code_btn.pack(side="left", padx=6)

    close_btn = tk.Button(
        button_frame, text="Close", command=root.destroy,
        bg=COLOR_SURFACE, fg=COLOR_TEXT, activebackground=COLOR_GOLD,
        activeforeground=COLOR_BG, relief="flat", padx=14, pady=6,
        font=body_font, cursor="hand2",
    )
    close_btn.pack(side="left", padx=6)

    tk.Label(
        root, text=f"v{VERSION}", font=small_font, fg=COLOR_TEXT_DIM, bg=COLOR_BG,
    ).pack(side="bottom", pady=6)

    def _on_destroy():
        if on_close:
            on_close()

    root.protocol("WM_DELETE_WINDOW", lambda: (_on_destroy(), root.destroy()))
    root.mainloop()


def mark_paired(status_setter: Callable[[str], None], device_label: str = "a device") -> None:
    """Call from the server's pairing-success handler to update the
    open window's status text, if the window is still open. Callers
    that don't hold a reference to status_var can ignore this - the
    window is a convenience, not the source of truth (server.py's
    ApprovalManager/pairing_token check is the real gate)."""
    status_setter(f"Paired with {device_label}.")


def run_in_background(
    generate_code: Callable[[], str],
    device_name: str,
    port: int,
    on_close: Optional[Callable[[], None]] = None,
) -> threading.Thread:
    """Runs show_pairing_window() on its own thread so it doesn't block
    the caller (e.g. agent/main.py's server loop). Tkinter's mainloop
    must own its own thread; do not call Tkinter APIs from other threads
    once this is running."""
    thread = threading.Thread(
        target=show_pairing_window,
        args=(generate_code, device_name, port, on_close),
        daemon=True,
        name="chronix-pairing-ui",
    )
    thread.start()
    return thread
