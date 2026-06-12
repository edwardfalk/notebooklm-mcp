"""Drift smoke tests against the installed notebooklm-py.

This server hand-maps notebooklm-py's enums, dataclass fields, exceptions,
and method signatures into MCP tools. notebooklm-py is reverse-engineered
and moves fast, so every assumption the tool code makes is asserted here.
If an upstream bump breaks one of these, the failure names the exact
attribute or parameter that drifted — fix the tool code, then update the
expectation here.

The private ``notebooklm._*`` module imports are deliberate: the sub-API
classes are only reachable as instance attributes on an authenticated
client, and these tests must run without credentials.
"""

from __future__ import annotations

import inspect
from typing import get_args

import pytest
from notebooklm._artifacts import ArtifactsAPI
from notebooklm._chat import ChatAPI
from notebooklm._notebooks import NotebooksAPI
from notebooklm._research import ResearchAPI
from notebooklm._settings import SettingsAPI
from notebooklm._sources import SourcesAPI
from notebooklm.client import NotebookLMClient
from notebooklm.types import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    AskResult,
    ChatMode,
    ChatReference,
    GenerationStatus,
    Notebook,
    NotebookDescription,
    ReportFormat,
    Source,
    SourceFulltext,
    SourceStatus,
    SuggestedTopic,
)

import enums

# ---------------------------------------------------------------------------
# Dataclass fields / properties the serializers in tools/*.py read
# ---------------------------------------------------------------------------

# (type, attributes accessed directly), getattr()-guarded access included —
# a getattr fallback hides drift just as silently as a hard AttributeError.
ATTRS_READ_BY_TOOLS = [
    (Artifact, ["id", "title", "kind", "status"]),
    (Notebook, ["id", "title", "is_owner", "created_at"]),
    (NotebookDescription, ["summary", "suggested_topics"]),
    (SuggestedTopic, ["question"]),
    (Source, ["id", "title", "url", "kind", "status"]),
    (SourceFulltext, ["source_id", "title", "kind", "url", "char_count", "content"]),
    (GenerationStatus, ["task_id", "url", "error", "error_code", "is_complete", "is_failed"]),
    (AskResult, ["answer", "conversation_id", "turn_number", "is_follow_up", "references"]),
    (ChatReference, ["citation_number", "cited_text", "source_id"]),
]


@pytest.mark.parametrize(
    "cls,attrs", ATTRS_READ_BY_TOOLS, ids=lambda v: v.__name__ if isinstance(v, type) else ""
)
def test_attributes_read_by_tools_exist(cls, attrs):
    fields = set(getattr(cls, "__dataclass_fields__", {}))
    for attr in attrs:
        assert attr in fields or hasattr(cls, attr), (
            f"{cls.__name__}.{attr} is gone from notebooklm-py — "
            f"a tool serializer reads it"
        )


def test_generation_status_metadata_field_still_exists():
    # _status_to_dict() pops "metadata" from asdict(); if the field is
    # renamed the pop silently becomes a no-op and internal data leaks
    # into tool output.
    assert "metadata" in GenerationStatus.__dataclass_fields__


# ---------------------------------------------------------------------------
# Enum maps: Literal aliases in enums.py must match the library enums
# ---------------------------------------------------------------------------

LITERAL_MAP_PAIRS = [
    ("audio_format", enums.AudioFormatLiteral, enums.AUDIO_FORMAT_MAP),
    ("audio_length", enums.AudioLengthLiteral, enums.AUDIO_LENGTH_MAP),
    ("video_format", enums.VideoFormatLiteral, enums.VIDEO_FORMAT_MAP),
    ("video_style", enums.VideoStyleLiteral, enums.VIDEO_STYLE_MAP),
    ("slide_format", enums.SlideDeckFormatLiteral, enums.SLIDE_DECK_FORMAT_MAP),
    ("slide_length", enums.SlideDeckLengthLiteral, enums.SLIDE_DECK_LENGTH_MAP),
    ("orientation", enums.InfographicOrientationLiteral, enums.INFOGRAPHIC_ORIENTATION_MAP),
    ("detail_level", enums.InfographicDetailLiteral, enums.INFOGRAPHIC_DETAIL_MAP),
    ("quantity", enums.QuizQuantityLiteral, enums.QUIZ_QUANTITY_MAP),
    ("difficulty", enums.QuizDifficultyLiteral, enums.QUIZ_DIFFICULTY_MAP),
    ("goal", enums.ChatGoalLiteral, enums.CHAT_GOAL_MAP),
    ("response_length", enums.ChatResponseLengthLiteral, enums.CHAT_RESPONSE_LENGTH_MAP),
]


@pytest.mark.parametrize("name,literal,mapping", LITERAL_MAP_PAIRS, ids=lambda v: v if isinstance(v, str) else "")
def test_literal_matches_enum_map(name, literal, mapping):
    # The Literal is what the LLM sees in the JSON schema; the map is what
    # lookup_enum accepts. They must be identical or a schema-legal value
    # raises ValueError at runtime (or a legal value is hidden from the LLM).
    assert set(get_args(literal)) == set(mapping), f"{name}: Literal and enum map diverged"
    assert mapping, f"{name}: enum map is empty — upstream enum vanished?"


@pytest.mark.parametrize(
    "literal,enum_cls",
    [(enums.ReportFormatLiteral, ReportFormat), (enums.ChatModeLiteral, ChatMode)],
    ids=["ReportFormat", "ChatMode"],
)
def test_str_enum_literals_constructible(literal, enum_cls):
    # These two are str-valued enums; tool code calls the constructor
    # directly (ReportFormat(value), ChatMode(value)) instead of a map.
    for value in get_args(literal):
        enum_cls(value)


@pytest.mark.parametrize(
    "labels,enum_cls",
    [
        (enums.SOURCE_STATUS_LABELS, SourceStatus),
        (enums.ARTIFACT_STATUS_LABELS, ArtifactStatus),
    ],
    ids=["SourceStatus", "ArtifactStatus"],
)
def test_status_labels_cover_all_members(labels, enum_cls):
    # status_label degrades unknown codes to raw ints, so a new upstream
    # status won't break listing — but this test forces a conscious label
    # choice when one appears.
    assert set(labels) == set(enum_cls), (
        f"{enum_cls.__name__} members changed — update the label map in enums.py"
    )


def test_artifact_type_filter_values():
    # list_artifacts' docstring promises these filter strings.
    documented = {
        "audio", "video", "slide_deck", "mind_map", "infographic",
        "quiz", "flashcards", "report", "data_table",
    }
    accepted = {t.value for t in ArtifactType}
    missing = documented - accepted
    assert not missing, f"ArtifactType lost values the docstring promises: {missing}"


# ---------------------------------------------------------------------------
# Client API surface: every method + keyword the tool bodies call
# ---------------------------------------------------------------------------

# (api class, method name, parameter names passed by tool code)
API_SURFACE = [
    (NotebooksAPI, "list", []),
    (NotebooksAPI, "create", ["title"]),
    (NotebooksAPI, "get_description", ["notebook_id"]),
    (NotebooksAPI, "get_summary", ["notebook_id"]),  # fallback parse path
    (NotebooksAPI, "rename", ["notebook_id", "new_title"]),
    (NotebooksAPI, "delete", ["notebook_id"]),
    (SourcesAPI, "add_url", ["notebook_id", "url", "wait", "wait_timeout"]),
    # tools/sources.py passes the body positionally; the library names it "content"
    (SourcesAPI, "add_text", ["notebook_id", "title", "content", "wait", "wait_timeout"]),
    (SourcesAPI, "add_file", ["notebook_id", "wait", "wait_timeout"]),
    (SourcesAPI, "list", ["notebook_id"]),
    (SourcesAPI, "get_fulltext", ["notebook_id", "source_id"]),
    (SourcesAPI, "delete", ["notebook_id", "source_id"]),
    (ResearchAPI, "start", ["notebook_id", "query", "source", "mode"]),
    (ResearchAPI, "poll", ["notebook_id"]),
    (ResearchAPI, "import_sources", ["notebook_id", "task_id", "sources"]),
    (ChatAPI, "ask", ["notebook_id", "question", "source_ids", "conversation_id"]),
    (ChatAPI, "set_mode", ["notebook_id", "mode"]),
    (ChatAPI, "configure", ["notebook_id", "goal", "response_length", "custom_prompt"]),
    (ArtifactsAPI, "generate_audio",
     ["notebook_id", "source_ids", "language", "instructions", "audio_format", "audio_length"]),
    (ArtifactsAPI, "generate_video",
     ["notebook_id", "source_ids", "language", "instructions", "video_format", "video_style"]),
    (ArtifactsAPI, "generate_slide_deck",
     ["notebook_id", "source_ids", "language", "instructions", "slide_format", "slide_length"]),
    (ArtifactsAPI, "generate_mind_map", ["notebook_id", "source_ids"]),
    (ArtifactsAPI, "generate_infographic",
     ["notebook_id", "source_ids", "language", "instructions", "orientation", "detail_level"]),
    (ArtifactsAPI, "generate_quiz",
     ["notebook_id", "source_ids", "instructions", "quantity", "difficulty"]),
    (ArtifactsAPI, "generate_flashcards",
     ["notebook_id", "source_ids", "instructions", "quantity", "difficulty"]),
    (ArtifactsAPI, "generate_report",
     ["notebook_id", "report_format", "source_ids", "language", "custom_prompt"]),
    (ArtifactsAPI, "generate_data_table",
     ["notebook_id", "source_ids", "language", "instructions"]),
    (ArtifactsAPI, "list", ["notebook_id", "artifact_type"]),
    (ArtifactsAPI, "poll_status", ["notebook_id", "task_id"]),
    (ArtifactsAPI, "wait_for_completion", ["notebook_id", "task_id", "timeout"]),
    (ArtifactsAPI, "download_audio", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_video", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_slide_deck", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_infographic", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_report", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_data_table", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_mind_map", ["notebook_id", "output_path", "artifact_id"]),
    (ArtifactsAPI, "download_quiz",
     ["notebook_id", "output_path", "artifact_id", "output_format"]),
    (ArtifactsAPI, "download_flashcards",
     ["notebook_id", "output_path", "artifact_id", "output_format"]),
    (SettingsAPI, "set_output_language", ["language"]),
    (SettingsAPI, "get_output_language", []),
]


@pytest.mark.parametrize(
    "api_cls,method,params",
    API_SURFACE,
    ids=[f"{cls.__name__}.{m}" for cls, m, _ in API_SURFACE],
)
def test_api_method_signature(api_cls, method, params):
    fn = getattr(api_cls, method, None)
    assert fn is not None, f"{api_cls.__name__}.{method} no longer exists"
    assert inspect.iscoroutinefunction(fn), f"{api_cls.__name__}.{method} is no longer async"
    sig_params = inspect.signature(fn).parameters
    accepts_kwargs = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in sig_params.values()
    )
    for param in params:
        assert param in sig_params or accepts_kwargs, (
            f"{api_cls.__name__}.{method} lost parameter {param!r}"
        )


def test_client_from_storage_exists():
    # _runtime._lifespan boots the client with this exact classmethod and
    # then enters it as an async context manager.
    assert inspect.iscoroutinefunction(NotebookLMClient.from_storage)
    assert hasattr(NotebookLMClient, "__aenter__")
    assert hasattr(NotebookLMClient, "__aexit__")


def test_wait_for_completion_still_raises_timeout_error():
    # wait_for_artifact's except TimeoutError branch depends on this; if the
    # library switches to returning a status or raising its own exception,
    # the tool would propagate an unhandled error instead of a clean
    # {"status": "in_progress"} payload.
    src = inspect.getsource(ArtifactsAPI.wait_for_completion)
    assert "raise TimeoutError" in src, (
        "wait_for_completion no longer raises TimeoutError — "
        "update tools/artifacts.py wait_for_artifact"
    )
