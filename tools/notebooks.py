"""Notebook-management MCP tools."""

from __future__ import annotations

from _runtime import get_client, mcp
from errors import tool_errors


@mcp.tool()
@tool_errors
async def list_notebooks() -> list[dict]:
    """List every notebook in your NotebookLM account.

    Returns a list of ``{id, title, source_count, is_owner, created_at}``.
    Use this whenever you need a notebook id and the user hasn't given one,
    or to confirm that a notebook you just created is visible.
    """
    client = get_client()
    notebooks = await client.notebooks.list()
    return [
        {
            "id": nb.id,
            "title": nb.title,
            "source_count": nb.sources_count,
            "is_owner": nb.is_owner,
            "created_at": nb.created_at.isoformat() if nb.created_at else None,
        }
        for nb in notebooks
    ]


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
    """Return the NotebookLM-generated summary for a notebook.

    Wraps ``client.notebooks.get_summary`` — this is the real summary rendered
    in the NotebookLM UI, not a chat-generated approximation.
    """
    client = get_client()
    summary = await client.notebooks.get_summary(notebook_id)
    return {"notebook_id": notebook_id, "summary": summary}


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
