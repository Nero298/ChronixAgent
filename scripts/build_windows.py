"""
Build script: produces a single dist/ChronixAgent.exe via PyInstaller.

Run on a Windows machine (or Windows CI runner):
    python scripts/build_windows.py

Requires: pip install -r requirements/windows.txt
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = ROOT / "agent" / "main.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
EXE_NAME = "ChronixAgent"


def main() -> int:
    if sys.platform != "win32":
        print(
            "Warning: this script is intended to run on Windows to produce a "
            "Windows PE executable. Continuing anyway (e.g. for CI dry-runs), "
            "but the output will not be a valid Windows .exe unless run on "
            "Windows or via a Windows CI runner.",
            file=sys.stderr,
        )

    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", EXE_NAME,
        "--onefile",
        "--noconsole",
        "--icon", str(ROOT / "assets" / "chronix.ico"),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        # Keep the build lean - do not implicitly pull in unrelated packages.
        "--noconfirm",
        str(ENTRY_POINT),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("PyInstaller build failed.", file=sys.stderr)
        return result.returncode

    exe_path = DIST_DIR / f"{EXE_NAME}.exe"
    if exe_path.exists():
        print(f"Build succeeded: {exe_path}")
    else:
        print("Build finished but expected exe was not found - check PyInstaller output.",
              file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
