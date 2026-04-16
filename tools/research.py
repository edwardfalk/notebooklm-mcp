"""Deep Research MCP tools.

NotebookLM's Deep Research feature searches the web (or your Google Drive),
evaluates source trustworthiness, and produces a synthesized research report
plus a curated list of sources. It's the headline "power move" of the
workflow because it removes the bottleneck of manually finding sources.

The library splits it into three steps:

1. ``client.research.start(...)`` — kicks off a background task.
2. ``client.research.poll(...)`` — returns ``status`` plus ``sources`` and
   ``summary`` once complete.
3. ``client.research.import_sources(...)`` — pulls the top-N sources into
   the notebook so they become queryable.

We expose (1) as ``start_deep_research`` and collapse (2) and (3) into
``check_research_status`` with an optional ``import_top_k`` parameter. No
blocking ``wait_for_research`` is exposed — the LLM polls cheaply instead.
"""

from __future__ import annotations

from typing import Any, Literal

from _runtime import get_client, mcp
from errors import tool_errors

# Status strings returned by client.research.poll(). Centralized so a library
# rename is a one-line fix rather than scattered literals.
_STATUS_COMPLETED = "completed"
_STATUS_IN_PROGRESS = "in_progress"
_STATUS_NO_RESEARCH = "no_research"


@mcp.tool()
@tool_errors
async def start_deep_research(
    notebook_id: str,
    query: str,
    mode: Literal["fast", "deep"] = "deep",
    source: Literal["web", "drive"] = "web",
) -> dict:
    """Start a Deep Research session against a notebook.

    **Prompting matters.** A solid Deep Research prompt is specific and
    time-bounded, e.g. ``"AI alignment and safety challenges for frontier
    models in 2026"``. Vague prompts like ``"AI alignment"`` produce a
    generic pull of sources. Include the outcome you care about, the domain,
    and the year.

    - ``mode="deep"`` (default) scans 30-50 sources and produces a full
      synthesis — takes 15-30+ minutes. Use for broad topics where you want
      comprehensive coverage.
    - ``mode="fast"`` scans ~5-10 sources and returns in under two minutes.
      Use for a quick scoping pass or when the topic is already tightly
      framed.
    - ``source="drive"`` only searches Google Drive; it does **not** support
      ``mode="deep"``.

    This call is non-blocking. It returns a task id immediately. Poll with
    ``check_research_status`` until ``status == "completed"`` and then call
    ``check_research_status`` again with ``import_top_k`` to import sources
    into the notebook.
    """
    client = get_client()
    result = await client.research.start(
        notebook_id=notebook_id,
        query=query,
        source=source,
        mode=mode,
    )
    if result is None:
        return {
            "status": "not_started",
            "message": (
                "research.start returned None; the server may have rejected the request. "
                "Check the notebook exists and the query is non-empty."
            ),
        }
    return {
        "status": "started",
        "task_id": result.get("task_id"),
        "report_id": result.get("report_id"),
        "notebook_id": result.get("notebook_id"),
        "query": result.get("query"),
        "mode": result.get("mode"),
    }


@mcp.tool()
@tool_errors
async def check_research_status(
    notebook_id: str,
    import_top_k: int | None = None,
) -> dict:
    """Check a Deep Research session's status and (optionally) import sources.

    Returns a ``status`` field which is one of:

    - ``"no_research"`` — nothing in flight for this notebook (not an error,
      just a normal resting state).
    - ``"in_progress"`` — Deep Research is still running. Poll again in 30-60
      seconds.
    - ``"completed"`` — research finished. ``sources`` is a list of
      ``{url, title}`` dicts and ``summary`` is the synthesized report text.

    When ``status == "completed"`` **and** ``import_top_k`` is set, this call
    also imports the first ``import_top_k`` sources into the notebook via
    ``research.import_sources`` and returns their new source ids under
    ``imported_sources``. This saves a round-trip — you do not need to call
    a separate import tool.

    Typical flow:

    1. ``start_deep_research(notebook_id, query="...", mode="deep")``
    2. Loop: ``check_research_status(notebook_id)`` every 30-60 seconds.
    3. Once ``status == "completed"``: ``check_research_status(notebook_id,
       import_top_k=15)`` to import the top 15 sources.
    """
    client = get_client()
    poll_result = await client.research.poll(notebook_id)

    # research.poll returns {"status": "no_research"} or {"status": "in_progress", ...}
    # or {"status": "completed", "sources": [...], "summary": ..., "task_id": ...}.
    status = poll_result.get("status")
    response: dict[str, Any] = {
        "notebook_id": notebook_id,
        "status": status,
    }
    for key in ("task_id", "query", "summary", "sources"):
        if key in poll_result:
            response[key] = poll_result[key]

    if status == _STATUS_COMPLETED and import_top_k is not None:
        if import_top_k <= 0:
            raise ValueError("import_top_k must be a positive integer")
        sources = poll_result.get("sources") or []
        task_id = poll_result.get("task_id")
        if not task_id:
            response["imported_sources"] = []
            response["import_error"] = (
                "research poll returned status=completed but no task_id; "
                "cannot import sources"
            )
            return response
        top_sources = sources[:import_top_k]
        imported = await client.research.import_sources(
            notebook_id=notebook_id,
            task_id=task_id,
            sources=top_sources,
        )
        response["imported_sources"] = imported
        response["imported_count"] = len(imported)

    return response
