"""Source-management MCP tools."""

from __future__ import annotations

from _runtime import get_client, mcp
from enums import SOURCE_STATUS_LABELS, kind_label, status_label
from errors import tool_errors, validate_path

# Default window for get_source_fulltext. A full web page routinely indexes
# to 50k+ characters, which overflows MCP tool-result limits; 20k is large
# enough for most documents while staying well inside them.
FULLTEXT_DEFAULT_MAX_CHARS = 20_000


def _source_to_dict(source) -> dict:
    """Serialize a ``Source`` dataclass for MCP return values."""
    return {
        "id": source.id,
        "title": source.title,
        "url": getattr(source, "url", None),
        "kind": kind_label(getattr(source, "kind", None)),
        "status": status_label(getattr(source, "status", None), SOURCE_STATUS_LABELS),
    }


def _window(content: str, offset: int, max_chars: int) -> dict:
    """Slice ``content`` into a pagination window with continuation hints."""
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    total = len(content)
    chunk = content[offset : offset + max_chars]
    end = offset + len(chunk)
    return {
        "char_count": total,
        "offset": offset,
        "returned_chars": len(chunk),
        "truncated": end < total,
        "next_offset": end if end < total else None,
        "content": chunk,
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
async def list_sources(notebook_id: str) -> dict:
    """List every source in a notebook with id, title, URL, kind, and status.

    Essential for "surgical source selection" — call this to get the source
    ids you want to pass as ``source_ids`` to ``ask_notebook`` or the
    ``generate_*`` tools for a focused, subset-only query or artifact.
    """
    client = get_client()
    sources = await client.sources.list(notebook_id)
    return {"sources": [_source_to_dict(s) for s in sources]}


@mcp.tool()
@tool_errors
async def get_source_fulltext(
    notebook_id: str,
    source_id: str,
    offset: int = 0,
    max_chars: int = FULLTEXT_DEFAULT_MAX_CHARS,
) -> dict:
    """Return the indexed text of a single source, windowed by ``offset``/``max_chars``.

    Use this when the user wants to quote from a source verbatim, or when you
    need to verify what NotebookLM actually indexed (which can differ from
    the original document — PDFs lose formatting, YouTube returns
    transcripts, etc.).

    Large sources (web pages routinely index to 50k+ characters) are paged:
    the response carries ``char_count`` (total), ``truncated``, and
    ``next_offset`` — pass ``next_offset`` back as ``offset`` to continue
    reading. The default window is 20,000 characters.
    """
    client = get_client()
    fulltext = await client.sources.get_fulltext(notebook_id, source_id)
    result = {
        "source_id": fulltext.source_id,
        "title": fulltext.title,
        "kind": kind_label(getattr(fulltext, "kind", None)),
        "url": getattr(fulltext, "url", None),
    }
    result.update(_window(fulltext.content or "", offset, max_chars))
    return result


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
