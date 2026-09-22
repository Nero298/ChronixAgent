# Chronix Agent

A lightweight AI agent that lets an Android phone control a Windows PC over
the same LAN/Wi-Fi, using Gemini as the natural-language planning brain and
a strict risk/approval pipeline before anything destructive runs.

Built by refactoring the `Zisu_AI-main` base project. See the sections
below for exactly what was reused, refactored, and newly built.

---

## A. What was found in the original Zisu base

- Python backend (`server.py`, Flask) + a fully local, no-cloud NLP
  pipeline: TF-IDF/Logistic-Regression intent router → per-skill BIO-tag
  extractors → plan builder → executor, with a feedback-logging loop.
- Skills: `open_app` (Start-Menu scan + rapidfuzz matching),
  `create_file`, `create_directory`, `delete_file_or_dir`.
- Electron frontend (`app/`, `admin/`) with a Node/npm toolchain.
- Declared requirements: Python 3.12+, Node 22+ — both incompatible with
  the Windows 7 / 2 GB RAM target here.

## B. What was reused

- The Start-Menu-scan + rapidfuzz app-matching logic from
  `core/app_helper.py`, adapted into `skills/apps/launcher.py` with only
  light changes (clean return shape, graceful "not found" handling).
- The general shape of "skills as small independent modules" carried
  forward into `skills/{apps,browser,files,cleanup,system}/`.

## C. What was refactored

- The entire local-ML intent/router layer is replaced: Chronix uses
  Gemini for natural-language understanding instead of a trained
  TF-IDF/logistic-regression classifier, because the spec calls for
  Gemini as the planning brain (this is a deliberate architecture change,
  not an oversight — the two approaches don't coexist well on a
  resource-constrained target).
- `delete_file_or_dir`-style logic became two distinct, independently
  guarded actions (`delete_file`, `delete_directory`) with explicit
  protected-path checks (`core/security.py`) that the original project
  didn't have.

## D. What was newly implemented

- `core/constants.py` — central action/risk/protocol constants.
- `core/models.py` — Action / ActionPlan / ApprovalRequest / ActionResult.
- `agent/gemini.py` — Gemini API client, JSON-only structured output.
- `core/plan_parser.py` — strict validator: whitelist-only actions, risk
  is always recomputed from our own table (never trusted from Gemini),
  malformed/unknown output is dropped rather than executed.
- `core/security.py` (Chronix Guard) — path-traversal detection,
  protected-path blocklist, risk-based allow/require-approval decisions.
- `core/permissions.py` — approval lifecycle: exact request-ID matching,
  expiration, duplicate-response rejection.
- `core/planner.py` — orchestrates Gemini → parser → Guard → (approval)
  → executor.
- `core/executor.py` — dispatch layer to skill modules.
- `agent/protocol.py` — JSON message envelope + encode/decode.
- `agent/server.py` — stdlib-only HTTP server (chat, approval response,
  pairing, pending-approvals polling, ping).
- `agent/discovery.py` — UDP broadcast beacon for LAN discovery.
- `agent/config.py`, `agent/logger.py`, `agent/startup.py`, `agent/main.py`
  — config loading, rotating logs, Scheduled-Task auto-start, entry point.
- Full Android app (`android/ChronixAgent/`) — Kotlin + Jetpack Compose:
  chat screen, connection status, approval dialog, settings/pairing
  screen, UDP discovery client, HTTP API client.
- `scripts/build_windows.py` — PyInstaller packaging script.
- `.github/workflows/build.yml` — CI building both `ChronixAgent.exe`
  and `ChronixAgent.apk`, plus running the test suite.
- `tests/` — 30 passing tests (unit + one real HTTP integration test that
  spins up the actual server and exercises it over the network).

## E. Final project structure

```
Chronix-Agent/
├── agent/           main.py, server.py, discovery.py, gemini.py,
│                    protocol.py, config.py, startup.py, logger.py
├── core/            constants.py, models.py, plan_parser.py,
│                    security.py, permissions.py, planner.py, executor.py
├── skills/          apps/, browser/, files/, cleanup/, system/
├── android/ChronixAgent/   Kotlin/Compose Android app
├── config/          config.example.json
├── requirements/    windows.txt
├── scripts/         build_windows.py
├── tests/           30 unit + integration tests
└── .github/workflows/build.yml
```

## F. How Gemini works

`agent/gemini.py` sends the user's message plus a system prompt that
forces Gemini to output **only** JSON matching the action-plan schema
(no prose, `responseMimeType: application/json`). The raw text is handed
to `core/plan_parser.py`, which is the actual security boundary:

- Unknown action names are dropped, not executed.
- Risk is **always** taken from `core/constants.ACTION_RISK`, never from
  whatever Gemini claims — so Gemini cannot talk its way into a lower
  risk tier for a dangerous action.
- Non-primitive/nested `params` values are stripped.
- A plan that isn't valid JSON, or is missing the `action_plan` type, is
  rejected outright — nothing partial executes from a malformed response.

## G. How Android ↔ PC LAN communication works

No VPS, no relay. `agent/discovery.py` broadcasts a small UDP JSON
beacon (`{"service": "chronix-agent", "port": ..., "device_name": ...}`)
every 5 seconds; the Android app's `DiscoveryClient` listens for it and
learns the PC's IP automatically. After that, all communication is
direct HTTP POST to `http://PC_IP:PORT/` with a JSON body whose `type`
field selects the handler (see `agent/protocol.py` for the full message
catalog). Android polls `pending_approvals_request` every few seconds to
pick up any approval that chat triggered.

## H. How Chronix Guard works

`core/security.py`'s `ChronixGuard.evaluate()` runs on every action
*after* `plan_parser` has already validated it:

- Delete-class actions get their path independently normalized and
  checked against a protected-path blocklist (Windows, System32,
  Program Files, drive roots, `..` traversal) — this check does not
  trust the parser's risk field, it re-derives path safety itself.
- `low` risk → auto-executes.
- `medium` risk → executes immediately, or requires approval if
  `require_approval_for_medium` is set in config.
- `high` risk → **always** requires approval, no exceptions, no config
  override.

## I. What requires approval

Any action whose risk is `high` (delete_file, delete_directory,
clear_cache, clear_app_data, shutdown, restart, terminate_process,
mass_file_operation), plus `medium`-risk actions if the admin has turned
on `require_approval_for_medium` in `config.json`.

## J. How auto-start works

`agent/startup.py` uses `schtasks.exe` (present since Windows XP, so
Windows-7-safe) to create a logon-triggered scheduled task. It always
checks `is_configured()` before creating anything, so repeated launches
never create duplicate tasks or loops. Controlled entirely by the
`auto_start` flag in `config.json`; `disable_auto_start()` removes it
cleanly.

## J.1 Pairing window (Windows side)

`agent/pairing_ui.py` opens a small, always-on-top Tkinter window (stdlib
only, no extra dependency) showing the current 6-digit pairing code in
gold-on-dark styling matching the Android app. This is the actual
mechanism that stops "same Wi-Fi = can control my PC": until a phone
successfully exchanges that code via the `/pair` endpoint
(`agent/server.py._handle_pair`), every other authenticated endpoint
rejects it (see `ChronixRequestHandler._authenticated`).

Controlled by `show_pairing_window` in `config.json` (default `true`).
Set it to `false` for a fully headless run once a phone is already
paired and you don't need to pair a new one.

## K. How to configure Gemini API

Never commit a real key. Either:

```bash
# Option 1: environment variable (preferred, always wins over config.json)
set CHRONIX_GEMINI_API_KEY=your-key-here      # Windows cmd
$env:CHRONIX_GEMINI_API_KEY="your-key-here"   # PowerShell

# Option 2: config/config.json (copy from config.example.json)
```

The Android app never holds, sends, or embeds this key — it only talks
to the already-running Windows agent.

## L. How to build Windows EXE

```bash
pip install -r requirements/windows.txt
python scripts/build_windows.py
# -> dist/ChronixAgent.exe
```

## M. How to build Android APK

```bash
cd android/ChronixAgent
# One-time, if gradlew isn't present yet:
gradle wrapper --gradle-version 8.4
./gradlew assembleRelease
# -> app/build/outputs/apk/release/app-release.apk
```

(Or simply open `android/ChronixAgent/` in Android Studio.)

## N. How to run GitHub Actions

Push to `main`, open a PR, or trigger manually via the "Run workflow"
button (`workflow_dispatch`) on `.github/workflows/build.yml`. It runs
the test suite, then builds both `ChronixAgent-Windows` and
`ChronixAgent-Android` as downloadable artifacts. No secrets are baked
into either build.

The Android job generates a fresh Gradle wrapper on every run (`gradle
wrapper --gradle-version 8.7`) rather than relying on a committed
`gradlew`/`gradle-wrapper.jar` — this repo intentionally doesn't commit
that binary jar. Gradle build caching uses the MIT-licensed "Basic"
provider (`cache-provider: basic`) rather than `gradle/actions`'
proprietary default, to keep the whole pipeline dependency-free of any
commercial Terms of Use. All third-party Action versions
(`actions/checkout@v7`, `actions/setup-python@v7`,
`actions/setup-java@v6`, `actions/upload-artifact@v7`,
`android-actions/setup-android@v4`, `gradle/actions/setup-gradle@v6`)
were verified against each project's own current documentation, not
guessed.

## O. Known limitations

- **No persistent WebSocket** — the current transport is plain HTTP
  request/response plus polling (`pending_approvals_request` every ~4s
  from Android). This is simple and Windows-7-friendly, but means up to
  a few seconds of latency before an approval prompt appears. A
  WebSocket upgrade is a natural next step but was not implemented yet.
- **`run_limited_command`, `edit_file`, `clear_app_data`,
  `mass_file_operation`** are recognized by the parser/guard (so a plan
  referencing them is validated and risk-classified correctly) but are
  **not wired to an executor** yet — they return "not yet implemented."
  This is deliberate: `run_limited_command` in particular needs a hard,
  reviewed per-command whitelist before it should ever run anything, and
  I didn't want to ship a vague "limited shell exec" that's really a
  general remote-code-execution primitive with a friendly name.
- **No tray icon** on Windows — the agent runs as a background process
  with console + file logging, plus the optional pairing window
  (`agent/pairing_ui.py`) for the pairing step specifically. A full tray
  icon with a menu (show pairing window, quit, etc.) is not built yet.
- Android app has not been built/run through an actual Gradle
  toolchain in this sandbox (no Android SDK/network access here) — the
  Kotlin source is complete and internally consistent with the Python
  wire format (verified by a real HTTP integration test on the Python
  side). The GitHub Actions workflow (`build-android` job) is the
  actual build verification path: it generates a real Gradle wrapper,
  installs the exact SDK platform/build-tools needed, and runs
  `./gradlew assembleRelease` on a real Ubuntu runner with a real
  Android SDK — this has not yet been triggered on a live repo as of
  this delivery, so the first push/PR is the real first build. Release
  signing is not configured, so the APK artifact is unsigned (fine for
  CI verification and side-loading, not for Play Store distribution).
- Minification/R8 (`isMinifyEnabled`) is deliberately OFF in the
  release build type. Compose + DataStore need tuned keep rules to
  survive R8 shrinking, and getting that wrong fails the build with
  opaque R8 errors. Re-enable once a real `proguard-rules.pro` has been
  validated against actual R8 output.
- The pairing window (`agent/pairing_ui.py`) is built on Tkinter, which
  ships with the standard Windows Python installer, but could not be
  visually tested in this sandbox (no display / no tkinter module
  available here) — only its logic, imports, and wiring into
  `agent/main.py` were verified.
- Windows-specific code paths (`schtasks`, `shutdown /s`, `taskkill`,
  Start Menu `.lnk` scanning) can only be *unit-tested* for their pure
  logic (path safety, protocol, risk rules) in this Linux sandbox — they
  have not been run on an actual Windows 7 machine yet.

## P. Exact files changed/created

All files under `Chronix-Agent/` in this delivery are new, written for
this project (see section E for the tree). The only *reused* logic (not
copied files) is the Start-Menu-scan/rapidfuzz matching approach from
`Zisu_AI-main/core/app_helper.py`, adapted into
`skills/apps/launcher.py`.

## Branding

- `assets/logo_icon.jpg` / `assets/logo_icon_square.png` — the compass/X
  mark, used to generate the Android launcher icon set
  (`android/ChronixAgent/app/src/main/res/mipmap-*`) and the Windows
  `.ico` (`assets/chronix.ico`, wired into `scripts/build_windows.py`).
- `assets/logo_wordmark.jpg` — the "ChroniX" wordmark, reference only
  (not currently baked into either build).
- Palette (`android/.../ui/theme/Color.kt`): deep teal-blue and near-black
  sampled directly from the logo, paired with a gold accent for
  user-message bubbles and interactive elements, matching the
  ChatGPT-style dark layout used in `ChatScreen.kt`.

## Quick start (development)

```bash
# Install deps
pip install -r requirements/windows.txt

# Run tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run the agent locally (Gemini key optional for testing non-AI paths)
set CHRONIX_GEMINI_API_KEY=your-key
python -m agent.main
```
