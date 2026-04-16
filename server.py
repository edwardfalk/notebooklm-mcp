"""NotebookLM MCP server entry point.

All tool definitions live under ``tools/`` and register themselves against
the shared ``FastMCP`` instance defined in :mod:`_runtime`. This module just
imports the tool packages (triggering their decorators) and starts the
server.
"""

from __future__ import annotations

from _runtime import mcp  # noqa: F401  (imported for its side-effect: FastMCP instance)

# Importing each tool module runs its @mcp.tool() decorators and registers
# the tools on the shared FastMCP instance. Order doesn't matter functionally
# but is grouped for readability.
import tools.notebooks  # noqa: F401,E402
import tools.sources  # noqa: F401,E402
import tools.research  # noqa: F401,E402
import tools.chat  # noqa: F401,E402
import tools.artifacts  # noqa: F401,E402
import tools.settings  # noqa: F401,E402


if __name__ == "__main__":
    mcp.run()
