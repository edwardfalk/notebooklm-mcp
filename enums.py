"""Literal <-> notebooklm-py enum maps.

MCP tool parameters are exposed as ``Literal["foo", "bar"]`` strings so
FastMCP can render them as JSON-schema enums (the LLM then sees the legal
values directly instead of having to read the docstring). This module does
the one-way translation from those strings into the Python enum types that
notebooklm-py's methods actually accept.

For ``int``-valued enums (AudioFormat, VideoStyle, etc.) we build a
``name.lower() -> member`` map per enum. For ``str``-valued enums
(ReportFormat, ChatMode) the library's own constructor already accepts the
lowercase string directly, so no map is needed — tool modules call the
constructor themselves.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Literal, TypeVar

from notebooklm.types import (
    ArtifactStatus,
    AudioFormat,
    AudioLength,
    ChatGoal,
    ChatResponseLength,
    InfographicDetail,
    InfographicOrientation,
    QuizDifficulty,
    QuizQuantity,
    SlideDeckFormat,
    SlideDeckLength,
    SourceStatus,
    VideoFormat,
    VideoStyle,
)

# ---------------------------------------------------------------------------
# Literal type aliases (exported for tool signatures)
# ---------------------------------------------------------------------------

AudioFormatLiteral = Literal["deep_dive", "brief", "critique", "debate"]
AudioLengthLiteral = Literal["short", "default", "long"]

VideoFormatLiteral = Literal["explainer", "brief"]
VideoStyleLiteral = Literal[
    "auto_select",
    "classic",
    "whiteboard",
    "kawaii",
    "anime",
    "watercolor",
    "retro_print",
    "heritage",
    "paper_craft",
]

SlideDeckFormatLiteral = Literal["detailed_deck", "presenter_slides"]
SlideDeckLengthLiteral = Literal["default", "short"]

InfographicOrientationLiteral = Literal["landscape", "portrait", "square"]
InfographicDetailLiteral = Literal["concise", "standard", "detailed"]

QuizQuantityLiteral = Literal["fewer", "standard", "more"]
QuizDifficultyLiteral = Literal["easy", "medium", "hard"]

QuizOutputFormatLiteral = Literal["json", "markdown", "html"]

# ReportFormat is a str enum; use ReportFormat(value) directly in tool code.
ReportFormatLiteral = Literal["briefing_doc", "study_guide", "blog_post", "custom"]

ChatGoalLiteral = Literal["default", "custom", "learning_guide"]
ChatResponseLengthLiteral = Literal["default", "longer", "shorter"]

# ChatMode is a str-valued Enum; use ChatMode(value) directly in tool code.
ChatModeLiteral = Literal["default", "learning_guide", "concise", "detailed"]


# ---------------------------------------------------------------------------
# Maps (one line each, built from each enum's members)
# ---------------------------------------------------------------------------


E = TypeVar("E", bound=Enum)


def _make_map(enum_cls: type[E], exclude: Iterable[str] = ()) -> dict[str, E]:
    """Build a ``name.lower() -> member`` dict from an ``Enum``.

    Uses ``__members__`` (not plain iteration) so aliases like
    ``QuizQuantity.MORE = 2`` — which is a duplicate of ``STANDARD = 2`` — are
    still addressable by their own name. ``exclude`` takes enum member names
    (case-insensitive) that should be rejected at the MCP boundary, e.g.
    ``VideoStyle.CUSTOM`` which requires additional setup the MCP doesn't
    support.
    """
    excluded = {name.upper() for name in exclude}
    return {
        name.lower(): member
        for name, member in enum_cls.__members__.items()
        if name.upper() not in excluded
    }


AUDIO_FORMAT_MAP = _make_map(AudioFormat)
AUDIO_LENGTH_MAP = _make_map(AudioLength)
VIDEO_FORMAT_MAP = _make_map(VideoFormat)
VIDEO_STYLE_MAP = _make_map(VideoStyle, exclude=("CUSTOM",))
SLIDE_DECK_FORMAT_MAP = _make_map(SlideDeckFormat)
SLIDE_DECK_LENGTH_MAP = _make_map(SlideDeckLength)
INFOGRAPHIC_ORIENTATION_MAP = _make_map(InfographicOrientation)
INFOGRAPHIC_DETAIL_MAP = _make_map(InfographicDetail)
QUIZ_QUANTITY_MAP = _make_map(QuizQuantity)
QUIZ_DIFFICULTY_MAP = _make_map(QuizDifficulty)
CHAT_GOAL_MAP = _make_map(ChatGoal)
CHAT_RESPONSE_LENGTH_MAP = _make_map(ChatResponseLength)


# ---------------------------------------------------------------------------
# Outbound serialization (library enums/ints -> clean strings for MCP output)
# ---------------------------------------------------------------------------

# Source.status and Artifact.status are raw ints in the library's dataclasses.
# These label maps mirror the library's own status semantics (rpc/types.py);
# ArtifactStatus.PROCESSING is labeled "in_progress" to stay consistent with
# the strings GenerationStatus already uses in check_artifact_status.
SOURCE_STATUS_LABELS: dict[int, str] = {
    SourceStatus.PROCESSING: "processing",
    SourceStatus.READY: "ready",
    SourceStatus.ERROR: "error",
    SourceStatus.PREPARING: "preparing",
}

ARTIFACT_STATUS_LABELS: dict[int, str] = {
    ArtifactStatus.PROCESSING: "in_progress",
    ArtifactStatus.PENDING: "pending",
    ArtifactStatus.COMPLETED: "completed",
    ArtifactStatus.FAILED: "failed",
}


def kind_label(kind: Enum | None) -> str | None:
    """Serialize a SourceType/ArtifactType member to its lowercase value.

    ``str(member)`` on these (str, Enum) classes yields ``"SourceType.PDF"``;
    the ``.value`` is the clean ``"pdf"`` the LLM should see.
    """
    if kind is None:
        return None
    value = getattr(kind, "value", None)
    return value if isinstance(value, str) else str(kind)


def status_label(status: int | None, labels: dict[int, str]) -> str | int | None:
    """Translate a raw status int into a readable label.

    Unknown codes pass through unchanged rather than erroring — a new
    upstream status should degrade to a visible int, not break listing.
    """
    if status is None:
        return None
    return labels.get(status, status)


def lookup_enum(param_name: str, value: str | None, mapping: dict[str, E]) -> E | None:
    """Translate a user-supplied string into the library enum value.

    Returns ``None`` when ``value`` is ``None`` so callers can pass the
    sentinel through to the underlying library (which uses ``None`` to mean
    "let the library pick the default"). An unknown string raises
    ``ValueError`` with a helpful list of allowed options.
    """
    if value is None:
        return None
    try:
        return mapping[value]
    except KeyError as exc:
        allowed = ", ".join(sorted(mapping))
        raise ValueError(
            f"{param_name}={value!r} is not a valid choice. Allowed values: {allowed}"
        ) from exc
