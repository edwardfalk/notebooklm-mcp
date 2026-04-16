"""Cross-cutting error handling + path safety for notebooklm-mcp tools.

Two things live here:

1. ``tool_errors`` — a decorator that wraps every MCP tool body and converts
   library exceptions into a uniform ``{"error": {...}}`` dict. The
   ``retryable`` hint lets autonomous loops decide whether to back off and
   retry without needing to parse a stack trace.

2. ``validate_path`` / ``prepare_output_path`` — guards used by
   ``add_source_file`` and every ``download_*_artifact`` tool. LLMs will
   absolutely try to write to ``/etc/passwd.mp3`` if you let them; this
   rejects anything that isn't an absolute path inside the user's home
   directory, unless the ``NOTEBOOKLM_MCP_ALLOW_ROOT=1`` env var is set.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from notebooklm.exceptions import (
    ArtifactDownloadError,
    ArtifactNotFoundError,
    ArtifactNotReadyError,
    ArtifactParseError,
    AuthError,
    ChatError,
    ClientError,
    ConfigurationError,
    NetworkError,
    NotebookLMError,
    NotebookNotFoundError,
    RateLimitError,
    RPCError,
    RPCTimeoutError,
    ServerError,
    SourceAddError,
    SourceNotFoundError,
    SourceProcessingError,
    SourceTimeoutError,
    ValidationError,
)

logger = logging.getLogger("notebooklm_mcp")


# Exception -> (error_type_string, retryable). Order is significant: the
# first class that matches via ``isinstance`` wins, so narrower subclasses
# must precede their bases.
_ERROR_TABLE: list[tuple[type[NotebookLMError], str, bool]] = [
    (RateLimitError, "rate_limit", True),
    (RPCTimeoutError, "timeout", True),
    (NetworkError, "network", True),
    (ServerError, "server", True),
    (AuthError, "auth", False),
    (ClientError, "client", False),
    (NotebookNotFoundError, "notebook_not_found", False),
    (SourceNotFoundError, "source_not_found", False),
    (SourceTimeoutError, "source_timeout", True),
    (SourceProcessingError, "source_processing", False),
    (SourceAddError, "source_add", False),
    (ArtifactNotFoundError, "artifact_not_found", False),
    (ArtifactNotReadyError, "artifact_not_ready", True),
    (ArtifactParseError, "artifact_parse", False),
    (ArtifactDownloadError, "artifact_download", True),
    (ChatError, "chat", False),
    (ValidationError, "validation", False),
    (ConfigurationError, "configuration", False),
    (RPCError, "rpc", False),
    (NotebookLMError, "notebooklm", False),  # base class catch-all
]


def _classify(exc: NotebookLMError) -> tuple[str, bool]:
    for cls, name, retryable in _ERROR_TABLE:
        if isinstance(exc, cls):
            return name, retryable
    # Unreachable: NotebookLMError is the last entry, so any instance
    # matches. Kept as a defensive fallback in case the table is edited.
    return "notebooklm", False


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def tool_errors(func: F) -> F:
    """Wrap an async MCP tool so library exceptions become structured errors.

    The returned coroutine resolves to either the tool's normal return value
    or ``{"error": {...}}``. Exceptions that are *not* ``NotebookLMError`` or
    ``ValueError`` (our enum-validation error type) propagate naturally —
    FastMCP surfaces them as protocol errors, which is the right behavior
    for a bug.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        tool_name = func.__name__
        try:
            result = await func(*args, **kwargs)
        except ValueError as exc:
            # Raised by our own enum validation (see enums.lookup_enum) and
            # by internal argument checks (e.g. wait_for_artifact clamping).
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "tool=%s status=validation duration_ms=%d msg=%s",
                tool_name,
                duration_ms,
                exc,
            )
            return {
                "error": {
                    "type": "validation",
                    "message": str(exc),
                    "retryable": False,
                }
            }
        except NotebookLMError as exc:
            error_type, retryable = _classify(exc)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "tool=%s status=error type=%s retryable=%s duration_ms=%d msg=%s",
                tool_name,
                error_type,
                retryable,
                duration_ms,
                exc,
            )
            payload: dict[str, Any] = {
                "type": error_type,
                "message": str(exc) or exc.__class__.__name__,
                "retryable": retryable,
            }
            # Surface extra fields that autonomous callers find useful.
            retry_after = getattr(exc, "retry_after", None)
            if retry_after is not None:
                payload["retry_after_seconds"] = retry_after
            status_code = getattr(exc, "status_code", None)
            if status_code is not None:
                payload["status_code"] = status_code
            return {"error": payload}

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("tool=%s status=ok duration_ms=%d", tool_name, duration_ms)
        return result

    return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


_HOME = Path(os.path.expanduser("~")).resolve()
_ALLOW_ROOT_ENV = "NOTEBOOKLM_MCP_ALLOW_ROOT"


class PathValidationError(ValueError):
    """Raised when a caller supplies an unsafe file path."""


def validate_path(path: str) -> str:
    """Resolve ``path`` and reject anything outside ``$HOME``.

    Returns the resolved absolute path string on success.

    Set ``NOTEBOOKLM_MCP_ALLOW_ROOT=1`` in the environment to bypass the
    home directory check (for CI/tmpdir scenarios).
    """
    if not path:
        raise PathValidationError("path must be a non-empty string")

    resolved = Path(os.path.expanduser(path)).resolve()

    if os.environ.get(_ALLOW_ROOT_ENV) == "1":
        return str(resolved)

    try:
        resolved.relative_to(_HOME)
    except ValueError as exc:
        raise PathValidationError(
            f"path {resolved!s} is outside $HOME ({_HOME!s}); "
            f"set {_ALLOW_ROOT_ENV}=1 to override"
        ) from exc
    return str(resolved)


def prepare_output_path(path: str) -> str:
    """Validate ``path`` and ensure its parent directory exists.

    Used by every ``download_*`` tool so the library's download methods
    don't fail with a bare ``FileNotFoundError`` on a fresh directory.
    """
    validated = validate_path(path)
    Path(validated).parent.mkdir(parents=True, exist_ok=True)
    return validated
