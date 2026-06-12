"""Unit tests for the outbound serialization helpers added after E2E testing.

These cover the pure functions that clean up library output before it
reaches the MCP client: enum/status labels, reference deduplication, and
fulltext windowing.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from notebooklm.types import ArtifactStatus, ArtifactType, SourceStatus, SourceType

from enums import (
    ARTIFACT_STATUS_LABELS,
    SOURCE_STATUS_LABELS,
    kind_label,
    status_label,
)
from tools.chat import _dedupe_references
from tools.notebooks import _parse_summary_blob
from tools.sources import _window


# ---------------------------------------------------------------------------
# kind_label / status_label
# ---------------------------------------------------------------------------


def test_kind_label_returns_clean_value():
    assert kind_label(SourceType.PASTED_TEXT) == "pasted_text"
    assert kind_label(ArtifactType.AUDIO) == "audio"


def test_kind_label_none():
    assert kind_label(None) is None


def test_status_label_known_codes():
    assert status_label(SourceStatus.READY, SOURCE_STATUS_LABELS) == "ready"
    assert status_label(2, SOURCE_STATUS_LABELS) == "ready"  # raw int from dataclass
    assert (
        status_label(ArtifactStatus.COMPLETED, ARTIFACT_STATUS_LABELS) == "completed"
    )
    assert status_label(1, ARTIFACT_STATUS_LABELS) == "in_progress"


def test_status_label_unknown_code_passes_through():
    assert status_label(99, SOURCE_STATUS_LABELS) == 99


def test_status_label_none():
    assert status_label(None, SOURCE_STATUS_LABELS) is None


# ---------------------------------------------------------------------------
# _dedupe_references
# ---------------------------------------------------------------------------


@dataclass
class _Ref:
    citation_number: int
    cited_text: str | None
    source_id: str


def test_dedupe_collapses_duplicate_citations():
    refs = [
        _Ref(1, "Position paper A", "src-a"),
        _Ref(2, "Position paper A", "src-a"),  # exact duplicate text+source
        _Ref(3, "Position paper B", "src-b"),
        _Ref(4, None, "src-a"),  # bare ref to already-cited source: dropped
        _Ref(5, "Position paper A", "src-b"),  # same text, different source: kept
    ]
    result = _dedupe_references(refs)
    assert [(r["source_id"], r["cited_text"]) for r in result] == [
        ("src-a", "Position paper A"),
        ("src-b", "Position paper B"),
        ("src-b", "Position paper A"),
    ]


def test_dedupe_keeps_one_bare_entry_for_textless_sources():
    refs = [
        _Ref(1, "quoted", "src-a"),
        _Ref(2, None, "src-c"),  # src-c never appears with text: keep one
        _Ref(3, None, "src-c"),
        _Ref(4, None, "src-c"),
    ]
    result = _dedupe_references(refs)
    assert len(result) == 2
    assert result[1] == {"citation_number": 2, "cited_text": None, "source_id": "src-c"}


def test_dedupe_empty():
    assert _dedupe_references([]) == []


# ---------------------------------------------------------------------------
# _window (fulltext paging)
# ---------------------------------------------------------------------------


def test_window_full_content_fits():
    result = _window("hello world", offset=0, max_chars=100)
    assert result == {
        "char_count": 11,
        "offset": 0,
        "returned_chars": 11,
        "truncated": False,
        "next_offset": None,
        "content": "hello world",
    }


def test_window_truncates_and_chains():
    content = "x" * 50
    first = _window(content, offset=0, max_chars=20)
    assert first["truncated"] is True
    assert first["next_offset"] == 20
    second = _window(content, offset=first["next_offset"], max_chars=20)
    third = _window(content, offset=second["next_offset"], max_chars=20)
    assert third["returned_chars"] == 10
    assert third["truncated"] is False
    assert third["next_offset"] is None
    total = first["content"] + second["content"] + third["content"]
    assert total == content


def test_window_offset_past_end():
    result = _window("abc", offset=10, max_chars=5)
    assert result["returned_chars"] == 0
    assert result["truncated"] is False


@pytest.mark.parametrize("offset,max_chars", [(-1, 10), (0, 0), (0, -5)])
def test_window_rejects_invalid_args(offset, max_chars):
    with pytest.raises(ValueError):
        _window("abc", offset=offset, max_chars=max_chars)


# ---------------------------------------------------------------------------
# _parse_summary_blob (get_notebook_summary fallback)
# ---------------------------------------------------------------------------

# Shape observed live from the SUMMARIZE RPC on 2026-06-12: an extra outer
# list level versus what notebooklm-py 0.3.x's get_description expects.
_REAL_SHAPE_BLOB = str(
    [
        ["The **MCP** is an open standard for connecting AI to tools."],
        [
            [
                ["What are the core features?", "Create a detailed briefing: core features"],
                ["Compare granular versus consolidated tools.", "Create a detailed briefing: compare"],
            ]
        ],
        None,
        None,
        None,
        [[["What are the core features?", 9], ["Compare granular versus consolidated tools.", 9]]],
    ]
)


def test_parse_summary_blob_real_shape():
    summary, topics = _parse_summary_blob(_REAL_SHAPE_BLOB)
    assert summary == "The **MCP** is an open standard for connecting AI to tools."
    assert topics == [
        "What are the core features?",
        "Compare granular versus consolidated tools.",
    ]


def test_parse_summary_blob_plain_text_passthrough():
    summary, topics = _parse_summary_blob("Just a plain prose summary.")
    assert summary == "Just a plain prose summary."
    assert topics == []


def test_parse_summary_blob_empty():
    assert _parse_summary_blob("") == ("", [])
