"""Notebook-management MCP tools."""

from __future__ import annotations

import ast

from _runtime import get_client, mcp
from errors import tool_errors


def _parse_summary_blob(blob: str) -> tuple[str, list[str]]:
    """Recover summary + suggested topics from ``get_summary``'s raw string.

    notebooklm-py 0.3.x's ``get_description`` mis-indexes the SUMMARIZE
    response (the payload gained an extra nesting level upstream) and returns
    empty fields. ``get_summary`` returns ``str(payload)`` instead —
    ``ast.literal_eval`` restores the structure so we can walk it.

    Heuristics, deliberately loose against further drift:
    - summary: descend first elements until the first string.
    - topics: any two-string list is a (question, prompt) pair; collect the
      questions, deduped, in order.

    A blob that isn't a list repr is assumed to already be plain summary text.
    """
    try:
        data = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return blob, []

    node = data
    while isinstance(node, list) and node:
        node = node[0]
    summary = node if isinstance(node, str) else ""

    topics: list[str] = []

    def walk(n: object) -> None:
        if not isinstance(n, list):
            return
        if len(n) == 2 and isinstance(n[0], str) and isinstance(n[1], str):
            if n[0] != summary and n[0] not in topics:
                topics.append(n[0])
            return
        for child in n:
            walk(child)

    walk(data)
    return summary, topics


@mcp.tool()
@tool_errors
async def list_notebooks() -> dict:
    """List every notebook in your NotebookLM account.

    Returns ``{"notebooks": [{id, title, is_owner, created_at}, ...]}``.
    Use this whenever you need a notebook id and the user hasn't given one,
    or to confirm that a notebook you just created is visible.

    Note: source counts are not included — the upstream API does not return
    them on the list endpoint. Use ``list_sources(notebook_id)`` to see a
    notebook's sources.
    """
    client = get_client()
    notebooks = await client.notebooks.list()
    return {
        "notebooks": [
            {
                "id": nb.id,
                "title": nb.title,
                "is_owner": nb.is_owner,
                "created_at": nb.created_at.isoformat() if nb.created_at else None,
            }
            for nb in notebooks
        ]
    }


@mcp.tool()
@tool_errors
async def create_notebook(title: str) -> dict:
    """Create a new NotebookLM notebook.

    Best practice (from field experience): name notebooks for the outcome and
    timeframe, e.g. ``"AI alignment frontier 2026"`` rather than
    ``"research"``. A specific title keeps the notebook focused and makes
    later source curation more effective.
    """
    client = get_client()
    notebook = await client.notebooks.create(title)
    return {"id": notebook.id, "title": notebook.title}


@mcp.tool()
@tool_errors
async def get_notebook_summary(notebook_id: str) -> dict:
    """Return the NotebookLM-generated summary and suggested topics for a notebook.

    The summary shown in the NotebookLM chat panel, plus the suggested
    follow-up questions. Tries the library's structured ``get_description``
    first; when that comes back empty (a known parsing bug against the
    current API response shape), falls back to recovering the structure
    from the raw ``get_summary`` blob.
    """
    client = get_client()
    description = await client.notebooks.get_description(notebook_id)
    summary = description.summary
    topics = [t.question for t in description.suggested_topics]
    if not summary:
        blob = await client.notebooks.get_summary(notebook_id)
        summary, topics = _parse_summary_blob(blob)
    return {
        "notebook_id": notebook_id,
        "summary": summary,
        "suggested_topics": topics,
    }


@mcp.tool()
@tool_errors
async def rename_notebook(notebook_id: str, new_title: str) -> dict:
    """Rename a notebook.

    Useful when you created a notebook with a placeholder title and learned
    the real topic after Deep Research ran.
    """
    client = get_client()
    notebook = await client.notebooks.rename(notebook_id, new_title)
    return {"id": notebook.id, "title": notebook.title}


@mcp.tool()
@tool_errors
async def delete_notebook(notebook_id: str) -> dict:
    """Permanently delete a notebook and all of its sources and artifacts.

    This is destructive. Ask the user to confirm before calling.
    """
    client = get_client()
    deleted = await client.notebooks.delete(notebook_id)
    return {"notebook_id": notebook_id, "deleted": bool(deleted)}
