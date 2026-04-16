"""Shared runtime state for the notebooklm-mcp server.

We keep the ``FastMCP`` instance and the singleton ``NotebookLMClient`` in a
module of their own so that every ``tools/*.py`` file can reach them without
creating a circular import with ``server.py``. ``server.py`` imports this
module and then imports each tool module so their ``@mcp.tool()`` decorators
fire and register tools against the shared instance.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP
from notebooklm import NotebookLMClient

# Configure logging to stderr; stdout is reserved for the MCP protocol.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("notebooklm_mcp")

_client: NotebookLMClient | None = None


@asynccontextmanager
async def _lifespan(_app: FastMCP) -> AsyncIterator[None]:
    """Initialize and tear down the NotebookLM client across the server lifespan."""
    global _client
    logger.info("Starting NotebookLM MCP server...")
    try:
        _client = await NotebookLMClient.from_storage()
    except Exception as exc:
        logger.error("Failed to load NotebookLM credentials: %s", exc)
        logger.error(
            "Run 'uv run notebooklm login' from the project directory to authenticate."
        )
        raise
    try:
        async with _client:
            logger.info("NotebookLM client initialized successfully")
            yield
    finally:
        logger.info("NotebookLM client closed")
        _client = None


mcp: FastMCP = FastMCP("NotebookLM", lifespan=_lifespan)


def get_client() -> NotebookLMClient:
    """Return the live NotebookLMClient singleton.

    Called by every tool body. Synchronous — the client itself is already
    set up by the lifespan, so there's no await-able work here. Making this
    ``async`` would force every caller into a pointless coroutine frame.
    """
    if _client is None:
        raise RuntimeError(
            "NotebookLM client is not initialized. "
            "Run 'uv run notebooklm login' and restart the MCP server."
        )
    return _client
