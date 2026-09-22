"""
Central constants for Chronix Agent.

Every action name, risk level, and protocol message type used anywhere
in the codebase MUST come from here. Do not scatter string literals.
"""

# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
PRODUCT_NAME = "Chronix Agent"
VERSION = "1.0.0"
DEFAULT_DEVICE_NAME = "Chronix-PC"
DEFAULT_SERVER_PORT = 8765
DISCOVERY_UDP_PORT = 8766
DISCOVERY_SERVICE_ID = "chronix-agent"

# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

ALL_RISK_LEVELS = (RISK_LOW, RISK_MEDIUM, RISK_HIGH)

# ---------------------------------------------------------------------------
# Action names
#
# This is the whitelist. The executor MUST refuse any action whose name
# is not a key in ACTION_RISK below. Gemini output is never trusted to
# invent new action names.
# ---------------------------------------------------------------------------

# Low risk - read-only / non-destructive / reversible
ACTION_OPEN_APP = "open_app"
ACTION_OPEN_BROWSER = "open_browser"
ACTION_OPEN_URL = "open_url"
ACTION_GET_SYSTEM_INFO = "get_system_info"
ACTION_LIST_FILES = "list_files"
ACTION_SEARCH_FILES = "search_files"
ACTION_GET_FILE_INFO = "get_file_info"

# Medium risk - creates / modifies non-critical user data
ACTION_CREATE_FILE = "create_file"
ACTION_EDIT_FILE = "edit_file"
ACTION_CREATE_DIRECTORY = "create_directory"
ACTION_MOVE_FILE = "move_file"
ACTION_COPY_FILE = "copy_file"
ACTION_RENAME_FILE = "rename_file"
ACTION_RUN_LIMITED_COMMAND = "run_limited_command"

# High risk - destructive or system-altering, always requires approval
ACTION_DELETE_FILE = "delete_file"
ACTION_DELETE_DIRECTORY = "delete_directory"
ACTION_CLEAR_CACHE = "clear_cache"
ACTION_CLEAR_APP_DATA = "clear_app_data"
ACTION_SHUTDOWN = "shutdown"
ACTION_RESTART = "restart"
ACTION_TERMINATE_PROCESS = "terminate_process"
ACTION_MASS_FILE_OPERATION = "mass_file_operation"

ACTION_RISK = {
    ACTION_OPEN_APP: RISK_LOW,
    ACTION_OPEN_BROWSER: RISK_LOW,
    ACTION_OPEN_URL: RISK_LOW,
    ACTION_GET_SYSTEM_INFO: RISK_LOW,
    ACTION_LIST_FILES: RISK_LOW,
    ACTION_SEARCH_FILES: RISK_LOW,
    ACTION_GET_FILE_INFO: RISK_LOW,

    ACTION_CREATE_FILE: RISK_MEDIUM,
    ACTION_EDIT_FILE: RISK_MEDIUM,
    ACTION_CREATE_DIRECTORY: RISK_MEDIUM,
    ACTION_MOVE_FILE: RISK_MEDIUM,
    ACTION_COPY_FILE: RISK_MEDIUM,
    ACTION_RENAME_FILE: RISK_MEDIUM,
    ACTION_RUN_LIMITED_COMMAND: RISK_MEDIUM,

    ACTION_DELETE_FILE: RISK_HIGH,
    ACTION_DELETE_DIRECTORY: RISK_HIGH,
    ACTION_CLEAR_CACHE: RISK_HIGH,
    ACTION_CLEAR_APP_DATA: RISK_HIGH,
    ACTION_SHUTDOWN: RISK_HIGH,
    ACTION_RESTART: RISK_HIGH,
    ACTION_TERMINATE_PROCESS: RISK_HIGH,
    ACTION_MASS_FILE_OPERATION: RISK_HIGH,
}

SUPPORTED_ACTIONS = frozenset(ACTION_RISK.keys())

# Required target-field name per action (for validation). None = no target needed.
ACTION_TARGET_FIELD = {
    ACTION_OPEN_APP: "target",
    ACTION_OPEN_BROWSER: "target",  # optional
    ACTION_OPEN_URL: "target",
    ACTION_GET_SYSTEM_INFO: None,
    ACTION_LIST_FILES: "target",
    ACTION_SEARCH_FILES: "target",
    ACTION_GET_FILE_INFO: "target",

    ACTION_CREATE_FILE: "target",
    ACTION_EDIT_FILE: "target",
    ACTION_CREATE_DIRECTORY: "target",
    ACTION_MOVE_FILE: "target",
    ACTION_COPY_FILE: "target",
    ACTION_RENAME_FILE: "target",
    ACTION_RUN_LIMITED_COMMAND: "target",

    ACTION_DELETE_FILE: "target",
    ACTION_DELETE_DIRECTORY: "target",
    ACTION_CLEAR_CACHE: "target",
    ACTION_CLEAR_APP_DATA: "target",
    ACTION_SHUTDOWN: None,
    ACTION_RESTART: None,
    ACTION_TERMINATE_PROCESS: "target",
    ACTION_MASS_FILE_OPERATION: "target",
}

# ---------------------------------------------------------------------------
# Protocol message types (Android <-> Agent JSON messages)
# ---------------------------------------------------------------------------
MSG_CHAT = "chat"
MSG_CHAT_RESPONSE = "chat_response"
MSG_APPROVAL_REQUEST = "approval_request"
MSG_APPROVAL_RESPONSE = "approval_response"
MSG_ACTION_RESULT = "action_result"
MSG_PAIR_REQUEST = "pair_request"
MSG_PAIR_RESPONSE = "pair_response"
MSG_PING = "ping"
MSG_PONG = "pong"
MSG_ERROR = "error"
MSG_PENDING_APPROVALS_REQUEST = "pending_approvals_request"
MSG_PENDING_APPROVALS_RESPONSE = "pending_approvals_response"

APPROVAL_DECISION_APPROVE = "approve"
APPROVAL_DECISION_REJECT = "reject"

# ---------------------------------------------------------------------------
# Approval system
# ---------------------------------------------------------------------------
APPROVAL_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# Protected system paths (Windows) - never touched even with approval
# ---------------------------------------------------------------------------
PROTECTED_PATH_FRAGMENTS = (
    "windows",
    "program files",
    "program files (x86)",
    "system32",
    "syswow64",
    "$recycle.bin",
    "boot",
    "programdata\\microsoft\\windows",
)

# Root-of-drive protection is handled by logic in security.py, not string
# matching, since "C:\" itself would never contain these fragments.
