"""Global NotebookLM settings MCP tools."""

from __future__ import annotations

from _runtime import get_client, mcp
from errors import tool_errors


@mcp.tool()
@tool_errors
async def set_output_language(language: str) -> dict:
    """Set the NotebookLM output language for generated artifacts.

    **IMPORTANT: this is a GLOBAL setting that affects every notebook in the
    user's account, not just the one you're working with.** Changing it will
    affect any future generation in any notebook until it's changed back.

    Use a language code such as ``"en"``, ``"es"``, ``"fr"``, ``"de"``,
    ``"ja"``, ``"ko"``, ``"zh_Hans"`` (Simplified Chinese), or ``"pt_BR"``.
    The full list is 80+ codes — see the NotebookLM docs for the complete
    catalog.

    For one-off overrides on a single generation call, prefer the
    ``language`` parameter on the generator tool instead of mutating the
    global setting.
    """
    client = get_client()
    result = await client.settings.set_output_language(language)
    return {"language": result, "scope": "global"}


@mcp.tool()
@tool_errors
async def get_output_language() -> dict:
    """Return the currently configured global output language code."""
    client = get_client()
    result = await client.settings.get_output_language()
    return {"language": result, "scope": "global"}
