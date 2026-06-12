"""Artifact generation, status tracking, and download MCP tools.

This module covers three concerns for NotebookLM's nine artifact types:

1. **Generation** — kick off an audio/video/slide/etc. generation task.
2. **Tracking** — list existing artifacts, check one's status, or wait
   (with a hard cap) for one to complete.
3. **Download** — write the finished artifact to a local file.

Every generator returns ``{task_id, artifact_id, status}``. Per the library,
``task_id`` **is** the artifact id — the same UUID is used for polling while
the task runs and as ``Artifact.id`` once it completes. We surface both keys
so downstream tools can pass whichever they prefer.

Mind maps are the exception: they are synchronous, return the mind-map JSON
plus a ``note_id`` inline, and must **not** be routed through
``wait_for_artifact`` (there's no task to wait on).
"""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from notebooklm.types import ArtifactType, ReportFormat

from _runtime import get_client, mcp
from enums import (
    ARTIFACT_STATUS_LABELS,
    AUDIO_FORMAT_MAP,
    AUDIO_LENGTH_MAP,
    INFOGRAPHIC_DETAIL_MAP,
    INFOGRAPHIC_ORIENTATION_MAP,
    QUIZ_DIFFICULTY_MAP,
    QUIZ_QUANTITY_MAP,
    SLIDE_DECK_FORMAT_MAP,
    SLIDE_DECK_LENGTH_MAP,
    VIDEO_FORMAT_MAP,
    VIDEO_STYLE_MAP,
    AudioFormatLiteral,
    AudioLengthLiteral,
    InfographicDetailLiteral,
    InfographicOrientationLiteral,
    QuizDifficultyLiteral,
    QuizOutputFormatLiteral,
    QuizQuantityLiteral,
    ReportFormatLiteral,
    SlideDeckFormatLiteral,
    SlideDeckLengthLiteral,
    VideoFormatLiteral,
    VideoStyleLiteral,
    kind_label,
    lookup_enum,
    status_label,
)
from errors import prepare_output_path, tool_errors

# Hard ceiling on how long any ``wait_for_artifact`` call may block. Two
# minutes is the soft default; five minutes is the absolute cap. Any longer
# and the LLM's tool turn starts to look unresponsive and the user can't
# interrupt cleanly — the skill teaches Claude to yield control instead.
WAIT_FOR_ARTIFACT_DEFAULT_SECONDS = 120
WAIT_FOR_ARTIFACT_HARD_CEILING = 300


def _status_to_dict(status) -> dict:
    """Serialize a library ``GenerationStatus`` for MCP return values.

    The library's ``GenerationStatus`` is a dataclass, so ``asdict`` handles
    the field enumeration. ``metadata`` is dropped (internal-only) and an
    ``artifact_id`` alias is added because the library documents that
    ``task_id == artifact_id`` — surfacing both lets downstream tools use
    whichever name makes the code clearer.
    """
    data = asdict(status)
    data.pop("metadata", None)
    data["artifact_id"] = data["task_id"]
    return data


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


@mcp.tool()
@tool_errors
async def generate_audio_overview(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    audio_format: AudioFormatLiteral | None = None,
    audio_length: AudioLengthLiteral | None = None,
    language: str = "en",
) -> dict:
    """Kick off an Audio Overview (podcast-style deep dive).

    **Give explicit instructions** — the default click is generic. Example:
    ``"Focus exclusively on the disagreements between AI safety researchers
    about alignment approaches, explain tradeoffs in simple language, keep
    this under fifteen minutes, and speak like a thoughtful senior engineer."``

    Optional controls:

    - ``audio_format``: ``"deep_dive"`` (default), ``"brief"``, ``"critique"``,
      ``"debate"``. Use ``"debate"`` when the sources disagree — it gives the
      most interesting output.
    - ``audio_length``: ``"short"``, ``"default"``, or ``"long"``.
    - ``source_ids``: restrict to a subset of sources for a focused overview.
    - ``language``: output language code (e.g. ``"en"``, ``"ja"``).

    Returns ``{task_id, artifact_id, status}``. Audio typically takes 2-10
    minutes (observed ~7 under load) and can rate-limit — poll with
    ``check_artifact_status``, block briefly with ``wait_for_artifact``, and
    if it's still running after one capped wait, yield to the user rather
    than looping. Call ``download_audio_artifact`` when
    ``status == "completed"``.
    """
    client = get_client()
    status = await client.artifacts.generate_audio(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
        audio_format=lookup_enum("audio_format", audio_format, AUDIO_FORMAT_MAP),
        audio_length=lookup_enum("audio_length", audio_length, AUDIO_LENGTH_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_video_overview(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    video_format: VideoFormatLiteral | None = None,
    video_style: VideoStyleLiteral | None = None,
    language: str = "en",
) -> dict:
    """Kick off a Video Overview.

    **Explicit visual style + content focus** beats the defaults. Example
    instructions: ``"Clean, modern blue-and-white color scheme with
    minimalist graphics and professional typography. Highlight the three
    main alignment schools and show why they disagree."``

    Controls:

    - ``video_format``: ``"explainer"`` (rich coverage, default) or
      ``"brief"`` (quick recap).
    - ``video_style``: ``"auto_select"``, ``"classic"``, ``"whiteboard"``,
      ``"kawaii"``, ``"anime"``, ``"watercolor"``, ``"retro_print"``,
      ``"heritage"``, ``"paper_craft"``.

    **Video takes 15-45 minutes.** Do not sit blocked — kick off the job,
    tell the user the expected wait, and poll with ``check_artifact_status``
    when they ask again. Use ``wait_for_artifact`` only for a short initial
    block (the default 120s is almost never enough for video).
    """
    client = get_client()
    status = await client.artifacts.generate_video(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
        video_format=lookup_enum("video_format", video_format, VIDEO_FORMAT_MAP),
        video_style=lookup_enum("video_style", video_style, VIDEO_STYLE_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_slide_deck(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    slide_format: SlideDeckFormatLiteral | None = None,
    slide_length: SlideDeckLengthLiteral | None = None,
    language: str = "en",
) -> dict:
    """Kick off a slide deck generation.

    - ``slide_format="presenter_slides"`` — minimal text, visual-first, best
      for live presentation.
    - ``slide_format="detailed_deck"`` — document-like slides with full text,
      best for standalone reading.
    - ``slide_length``: ``"default"`` or ``"short"``.
    """
    client = get_client()
    status = await client.artifacts.generate_slide_deck(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
        slide_format=lookup_enum("slide_format", slide_format, SLIDE_DECK_FORMAT_MAP),
        slide_length=lookup_enum("slide_length", slide_length, SLIDE_DECK_LENGTH_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_mind_map(
    notebook_id: str,
    source_ids: list[str] | None = None,
) -> dict:
    """Generate a mind map (synchronous — returns the JSON inline).

    Unlike the other generators, this is **not** an async task. It returns
    the mind-map JSON and a ``note_id`` immediately. Do not pass its return
    value through ``wait_for_artifact`` — there is no task to wait on.
    """
    client = get_client()
    result = await client.artifacts.generate_mind_map(
        notebook_id, source_ids=source_ids
    )
    return {
        "note_id": result.get("note_id"),
        "mind_map": result.get("mind_map"),
        "status": "completed",
    }


@mcp.tool()
@tool_errors
async def generate_infographic(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    orientation: InfographicOrientationLiteral | None = None,
    detail_level: InfographicDetailLiteral | None = None,
    language: str = "en",
) -> dict:
    """Kick off an infographic generation.

    **Field-tested settings**: ``orientation="landscape"`` and
    ``detail_level="standard"`` consistently look best. ``"detailed"`` tends
    to produce text-rendering errors; ``"concise"`` drops too much context.

    Instructions example: ``"Create a professional infographic mapping AI
    alignment approaches with names of representative researchers under each
    approach, using blue and gray colors and a clean layout."``
    """
    client = get_client()
    status = await client.artifacts.generate_infographic(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
        orientation=lookup_enum("orientation", orientation, INFOGRAPHIC_ORIENTATION_MAP),
        detail_level=lookup_enum("detail_level", detail_level, INFOGRAPHIC_DETAIL_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_quiz(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    quantity: QuizQuantityLiteral | None = None,
    difficulty: QuizDifficultyLiteral | None = None,
) -> dict:
    """Generate a quiz based on a notebook's sources.

    - ``difficulty``: ``"easy"``, ``"medium"``, ``"hard"``.
    - ``quantity``: ``"fewer"``, ``"standard"``, or ``"more"``.

    Note: quiz generation does **not** support a ``language`` parameter — it
    inherits the account's global output language.
    """
    client = get_client()
    status = await client.artifacts.generate_quiz(
        notebook_id,
        source_ids=source_ids,
        instructions=instructions,
        quantity=lookup_enum("quantity", quantity, QUIZ_QUANTITY_MAP),
        difficulty=lookup_enum("difficulty", difficulty, QUIZ_DIFFICULTY_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_flashcards(
    notebook_id: str,
    instructions: str | None = None,
    source_ids: list[str] | None = None,
    quantity: QuizQuantityLiteral | None = None,
    difficulty: QuizDifficultyLiteral | None = None,
) -> dict:
    """Generate study flashcards from a notebook's sources.

    Same controls as ``generate_quiz``. Pair with ``set_chat_mode("learning_guide")``
    before running for the best educational framing.
    """
    client = get_client()
    status = await client.artifacts.generate_flashcards(
        notebook_id,
        source_ids=source_ids,
        instructions=instructions,
        quantity=lookup_enum("quantity", quantity, QUIZ_QUANTITY_MAP),
        difficulty=lookup_enum("difficulty", difficulty, QUIZ_DIFFICULTY_MAP),
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_summary_report(
    notebook_id: str,
    custom_prompt: str | None = None,
    source_ids: list[str] | None = None,
    report_format: ReportFormatLiteral = "briefing_doc",
    language: str = "en",
) -> dict:
    """Generate a written report from a notebook's sources.

    Report formats:

    - ``"briefing_doc"`` (default) — executive briefing document.
    - ``"study_guide"`` — educational breakdown with sections and questions.
    - ``"blog_post"`` — blog-style long-form write-up.
    - ``"custom"`` — you must supply ``custom_prompt`` describing the shape
      of the report you want.

    This wraps ``client.artifacts.generate_report``, which takes
    ``custom_prompt`` directly (not an ``instructions`` string). When
    ``report_format == "custom"`` the ``custom_prompt`` is required.
    """
    client = get_client()
    status = await client.artifacts.generate_report(
        notebook_id,
        report_format=ReportFormat(report_format),
        source_ids=source_ids,
        language=language,
        custom_prompt=custom_prompt,
    )
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def generate_data_table(
    notebook_id: str,
    instructions: str,
    source_ids: list[str] | None = None,
    language: str = "en",
) -> dict:
    """Extract structured data from sources into a table.

    ``instructions`` is **required** — describe exactly what columns you
    want. Example: ``"Make a table of every study mentioned with columns:
    author, year, sample size, finding, effect size, and the source id it
    came from."``
    """
    client = get_client()
    status = await client.artifacts.generate_data_table(
        notebook_id,
        source_ids=source_ids,
        language=language,
        instructions=instructions,
    )
    return _status_to_dict(status)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@mcp.tool()
@tool_errors
async def list_artifacts(
    notebook_id: str, artifact_type: str | None = None
) -> dict:
    """List generated artifacts in a notebook.

    ``artifact_type`` is an optional filter matching ``ArtifactType`` values:
    ``"audio"``, ``"video"``, ``"slide_deck"``, ``"mind_map"``,
    ``"infographic"``, ``"quiz"``, ``"flashcards"``, ``"report"``,
    ``"data_table"``.
    """
    client = get_client()
    type_filter: ArtifactType | None = None
    if artifact_type is not None:
        try:
            type_filter = ArtifactType(artifact_type)
        except ValueError as exc:
            allowed = ", ".join(t.value for t in ArtifactType)
            raise ValueError(
                f"artifact_type={artifact_type!r} is not valid. Allowed: {allowed}"
            ) from exc

    artifacts = await client.artifacts.list(notebook_id, artifact_type=type_filter)
    return {
        "artifacts": [
            {
                "id": a.id,
                "title": a.title,
                "kind": kind_label(getattr(a, "kind", None)),
                "status": status_label(
                    getattr(a, "status", None), ARTIFACT_STATUS_LABELS
                ),
            }
            for a in artifacts
        ]
    }


@mcp.tool()
@tool_errors
async def check_artifact_status(notebook_id: str, task_id: str) -> dict:
    """Check the current status of a generation task (instant, non-blocking).

    Use this as the cheap first poll right after calling a ``generate_*``
    tool — it's a single API call. Only fall back to ``wait_for_artifact``
    when the status is still ``"pending"`` or ``"in_progress"`` and you're
    willing to block for up to ~2 minutes.
    """
    client = get_client()
    status = await client.artifacts.poll_status(notebook_id, task_id)
    return _status_to_dict(status)


@mcp.tool()
@tool_errors
async def wait_for_artifact(
    notebook_id: str,
    task_id: str,
    max_wait_seconds: int = WAIT_FOR_ARTIFACT_DEFAULT_SECONDS,
) -> dict:
    """Block (up to a hard cap) until an artifact finishes or fails.

    ``max_wait_seconds`` is clamped server-side to a ceiling of
    300 seconds. If the artifact is still running at the deadline, this
    returns ``{"status": "in_progress", "elapsed_seconds": ..., "hint": ...}``
    — call again or use ``check_artifact_status`` to poll.

    Video generation routinely takes 15-45 minutes. Do not loop this tool in
    a tight cycle waiting for video. Kick off the job, call
    ``wait_for_artifact`` once to see if it finishes quickly, and if not,
    **yield control to the user** and poll only when they ask again.
    """
    if max_wait_seconds <= 0:
        raise ValueError("max_wait_seconds must be positive")
    clamped = min(int(max_wait_seconds), WAIT_FOR_ARTIFACT_HARD_CEILING)

    client = get_client()
    start = time.monotonic()
    try:
        status = await client.artifacts.wait_for_completion(
            notebook_id,
            task_id,
            timeout=clamped,
        )
    except TimeoutError:
        # Library's internal poll loop hit its deadline. We already know
        # the artifact is still running — no need for another API call.
        return {
            "status": "in_progress",
            "task_id": task_id,
            "elapsed_seconds": int(time.monotonic() - start),
            "hint": (
                "Artifact is still running. Call check_artifact_status or "
                "wait_for_artifact again later. Video generation can take "
                "15-45 minutes."
            ),
        }

    elapsed = int(time.monotonic() - start)
    if status.is_complete:
        return {
            "status": "completed",
            "task_id": status.task_id,
            "artifact_id": status.task_id,
            "url": status.url,
            "elapsed_seconds": elapsed,
        }
    if status.is_failed:
        return {
            "status": "failed",
            "task_id": status.task_id,
            "error": status.error,
            "error_code": status.error_code,
            "elapsed_seconds": elapsed,
        }
    # Defensive fallback: wait_for_completion returned a non-terminal status
    # without raising. Shouldn't happen in normal flow but keeps the contract
    # consistent.
    return {
        "status": "in_progress",
        "task_id": status.task_id,
        "elapsed_seconds": elapsed,
        "hint": (
            "Artifact is still running. Call check_artifact_status or "
            "wait_for_artifact again later."
        ),
    }


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


async def _download_with_guard(
    method: str,
    notebook_id: str,
    output_path: str,
    artifact_id: str | None,
    **extra: Any,
) -> dict:
    """Shared logic for every ``download_*`` tool."""
    validated = prepare_output_path(output_path)
    client = get_client()
    download_fn = getattr(client.artifacts, method)
    written = await download_fn(
        notebook_id, validated, artifact_id=artifact_id, **extra
    )
    return {"path": written, "artifact_id": artifact_id}


@mcp.tool()
@tool_errors
async def download_audio_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed audio overview to a local file.

    The bytes are an MP4/AAC (DASH) container even though it's "audio" —
    prefer a ``.m4a`` extension (``.mp3`` also plays in most players but
    mislabels the codec).

    ``output_path`` must be absolute and inside ``$HOME`` unless
    ``NOTEBOOKLM_MCP_ALLOW_ROOT=1`` is set. Parent directories are created
    automatically. If ``artifact_id`` is omitted, the most recent audio
    artifact is used.
    """
    return await _download_with_guard(
        "download_audio", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_video_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed video overview to a local ``.mp4`` file."""
    return await _download_with_guard(
        "download_video", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_slide_deck_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed slide deck to a local ``.pdf`` file."""
    return await _download_with_guard(
        "download_slide_deck", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_infographic_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed infographic to a local ``.png`` file."""
    return await _download_with_guard(
        "download_infographic", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_report_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed report (briefing doc / study guide / blog post) as ``.md``."""
    return await _download_with_guard(
        "download_report", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_data_table_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a completed data table to a local ``.csv`` file."""
    return await _download_with_guard(
        "download_data_table", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_mind_map_artifact(
    notebook_id: str, output_path: str, artifact_id: str | None = None
) -> dict:
    """Download a mind map as hierarchical ``.json`` suitable for visualization.

    Note: ``generate_mind_map`` already returns the JSON inline. Use this
    tool only when you want to persist it to disk.
    """
    return await _download_with_guard(
        "download_mind_map", notebook_id, output_path, artifact_id
    )


@mcp.tool()
@tool_errors
async def download_quiz_artifact(
    notebook_id: str,
    output_path: str,
    artifact_id: str | None = None,
    output_format: QuizOutputFormatLiteral = "json",
) -> dict:
    """Download a completed quiz.

    ``output_format``: ``"json"`` (default), ``"markdown"``, or ``"html"``.
    Markdown is the best choice for pasting into a doc or printing.
    """
    return await _download_with_guard(
        "download_quiz",
        notebook_id,
        output_path,
        artifact_id,
        output_format=output_format,
    )


@mcp.tool()
@tool_errors
async def download_flashcards_artifact(
    notebook_id: str,
    output_path: str,
    artifact_id: str | None = None,
    output_format: QuizOutputFormatLiteral = "json",
) -> dict:
    """Download completed flashcards.

    ``output_format``: ``"json"`` (default), ``"markdown"``, or ``"html"``.
    """
    return await _download_with_guard(
        "download_flashcards",
        notebook_id,
        output_path,
        artifact_id,
        output_format=output_format,
    )
