"""Source-management MCP tools."""

from __future__ import annotations

from _runtime import get_client, mcp
from errors import tool_errors, validate_path


def _source_to_dict(source) -> dict:
    """Serialize a ``Source`` dataclass for MCP return values."""
    return {
        "id": source.id,
        "title": source.title,
        "url": getattr(source, "url", None),
        "kind": str(getattr(source, "kind", "")) or None,
        "status": getattr(source, "status", None),
    }


@mcp.tool()
@tool_errors
async def add_source_url(
    notebook_id: str,
    url: str,
    wait: bool = True,
    wait_timeout: float = 120.0,
) -> dict:
    """Add a web page, YouTube URL, or other URL-based source to a notebook.

    By default this waits up to ``wait_timeout`` seconds for the source to
    finish processing before returning. That matters: a source must be
    ``ready`` before ``ask_notebook`` or any ``generate_*`` tool can use it.
    Set ``wait=False`` only if you know you will poll or wait separately.
    """
    client = get_client()
    source = await client.sources.add_url(
        notebook_id, url, wait=wait, wait_timeout=wait_timeout
    )
    return _source_to_dict(source)


@mcp.tool()
@tool_errors
async def add_source_text(
    notebook_id: str,
    title: str,
    text: str,
    wait: bool = True,
    wait_timeout: float = 120.0,
) -> dict:
    """Add raw text as a source (e.g., pasted notes or a transcript snippet)."""
    client = get_client()
    source = await client.sources.add_text(
        notebook_id, title, text, wait=wait, wait_timeout=wait_timeout
    )
    return _source_to_dict(source)


@mcp.tool()
@tool_errors
async def add_source_file(
    notebook_id: str,
    file_path: str,
    wait: bool = True,
    wait_timeout: float = 120.0,
) -> dict:
    """Upload a local file as a source (PDF, .docx, .pptx, .md, .txt, audio, etc.).

    ``file_path`` must be an absolute path inside the user's home directory
    (or anywhere, if ``NOTEBOOKLM_MCP_ALLOW_ROOT=1`` is set). This is a hard
    guard against path-traversal mistakes — ask the user if you need access
    to a path outside ``$HOME``.
    """
    client = get_client()
    validated = validate_path(file_path)
    source = await client.sources.add_file(
        notebook_id, validated, wait=wait, wait_timeout=wait_timeout
    )
    return _source_to_dict(source)


@mcp.tool()
@tool_errors
async def list_sources(notebook_id: str) -> list[dict]:
    """List every source in a notebook with id, title, URL, kind, and status.

    Essential for "surgical source selection" — call this to get the source
    ids you want to pass as ``source_ids`` to ``ask_notebook`` or the
    ``generate_*`` tools for a focused, subset-only query or artifact.
    """
    client = get_client()
    sources = await client.sources.list(notebook_id)
    return [_source_to_dict(s) for s in sources]


@mcp.tool()
@tool_errors
async def get_source_fulltext(notebook_id: str, source_id: str) -> dict:
    """Return the full indexed text of a single source.

    Use this when the user wants to quote from a source verbatim, or when you
    need to verify what NotebookLM actually indexed (which can differ from
    the original document — PDFs lose formatting, YouTube returns
    transcripts, etc.).
    """
    client = get_client()
    fulltext = await client.sources.get_fulltext(notebook_id, source_id)
    return {
        "source_id": fulltext.source_id,
        "title": fulltext.title,
        "kind": str(getattr(fulltext, "kind", "")) or None,
        "url": getattr(fulltext, "url", None),
        "char_count": getattr(fulltext, "char_count", None),
        "content": fulltext.content,
    }


@mcp.tool()
@tool_errors
async def delete_source(notebook_id: str, source_id: str) -> dict:
    """Remove a source from a notebook.

    This is destructive and cannot be undone from the API. Ask the user to
    confirm before calling.
    """
    client = get_client()
    deleted = await client.sources.delete(notebook_id, source_id)
    return {"source_id": source_id, "deleted": bool(deleted)}
