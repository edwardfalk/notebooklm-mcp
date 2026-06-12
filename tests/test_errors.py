"""Tests for errors.py: classification table ordering and path guards."""

from __future__ import annotations

from pathlib import Path

import pytest
from notebooklm.exceptions import (
    DecodingError,
    NotebookLMError,
    NotebookNotFoundError,
    RateLimitError,
    RPCTimeoutError,
)

import errors
from errors import (
    PathValidationError,
    _classify,
    _ERROR_TABLE,
    prepare_output_path,
    validate_path,
)


# ---------------------------------------------------------------------------
# Error table
# ---------------------------------------------------------------------------


def test_error_table_has_no_unreachable_entries():
    # _classify walks the table top-down with isinstance, so a subclass
    # listed after its base can never match. Catch that at test time.
    for i, (earlier, _, _) in enumerate(_ERROR_TABLE):
        for later, name, _ in _ERROR_TABLE[i + 1 :]:
            assert not issubclass(later, earlier), (
                f"{later.__name__} ({name!r}) is unreachable: it is listed "
                f"after its base class {earlier.__name__}"
            )


def test_error_table_ends_with_base_catch_all():
    assert _ERROR_TABLE[-1][0] is NotebookLMError


@pytest.mark.parametrize(
    "exc,expected_type,expected_retryable",
    [
        (RateLimitError("slow down"), "rate_limit", True),
        (RPCTimeoutError("timed out"), "timeout", True),
        (NotebookNotFoundError("nb-123"), "notebook_not_found", False),
        # Subclasses with no entry of their own fall through to their base:
        # DecodingError -> RPCError, NotebookLMError -> catch-all.
        (DecodingError("bad blob"), "rpc", False),
        (NotebookLMError("anything"), "notebooklm", False),
    ],
)
def test_classify(exc, expected_type, expected_retryable):
    assert _classify(exc) == (expected_type, expected_retryable)


# ---------------------------------------------------------------------------
# tool_errors wrapper
# ---------------------------------------------------------------------------


def test_tool_errors_converts_library_exception():
    import asyncio

    @errors.tool_errors
    async def boom():
        raise RateLimitError("rate limited", retry_after=42)

    result = asyncio.run(boom())
    assert result["error"]["type"] == "rate_limit"
    assert result["error"]["retryable"] is True
    assert result["error"]["retry_after_seconds"] == 42


def test_tool_errors_converts_value_error():
    import asyncio

    @errors.tool_errors
    async def bad_arg():
        raise ValueError("nope")

    result = asyncio.run(bad_arg())
    assert result["error"] == {
        "type": "validation",
        "message": "nope",
        "retryable": False,
    }


def test_tool_errors_lets_unexpected_exceptions_propagate():
    import asyncio

    @errors.tool_errors
    async def bug():
        raise KeyError("a real bug")

    with pytest.raises(KeyError):
        asyncio.run(bug())


def test_tool_errors_passes_through_success():
    import asyncio

    @errors.tool_errors
    async def ok():
        return {"fine": True}

    assert asyncio.run(ok()) == {"fine": True}


# ---------------------------------------------------------------------------
# Path guards
# ---------------------------------------------------------------------------


def test_validate_path_accepts_home_paths(monkeypatch):
    monkeypatch.delenv(errors._ALLOW_ROOT_ENV, raising=False)
    inside = str(Path.home() / "Downloads" / "overview.mp3")
    assert validate_path(inside) == inside
    # Tilde expansion lands inside $HOME too.
    assert validate_path("~/overview.mp3") == str(Path.home() / "overview.mp3")


@pytest.mark.parametrize("bad", ["/etc/passwd.mp3", "/tmp/out.mp4", ""])
def test_validate_path_rejects_outside_home(bad, monkeypatch):
    monkeypatch.delenv(errors._ALLOW_ROOT_ENV, raising=False)
    with pytest.raises(PathValidationError):
        validate_path(bad)


def test_validate_path_rejects_traversal_out_of_home(monkeypatch):
    monkeypatch.delenv(errors._ALLOW_ROOT_ENV, raising=False)
    sneaky = str(Path.home() / ".." / ".." / "etc" / "passwd")
    with pytest.raises(PathValidationError):
        validate_path(sneaky)


def test_validate_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(errors._ALLOW_ROOT_ENV, "1")
    outside = str(tmp_path / "out.mp3")
    assert validate_path(outside) == outside


def test_path_validation_error_is_value_error():
    # tool_errors only catches ValueError/NotebookLMError; the path guard
    # must stay a ValueError subclass or guard failures crash the tool turn.
    assert issubclass(PathValidationError, ValueError)


def test_prepare_output_path_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv(errors._ALLOW_ROOT_ENV, "1")
    target = tmp_path / "new" / "nested" / "audio.mp3"
    result = prepare_output_path(str(target))
    assert result == str(target)
    assert target.parent.is_dir()
