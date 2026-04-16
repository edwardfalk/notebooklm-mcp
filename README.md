# NotebookLM MCP for Claude (Desktop & CLI)

A powerful MCP (Model Context Protocol) server that brings Google NotebookLM into Claude Desktop and Claude Code.

## Features

- **Deep Research**: Start, poll, and import results from NotebookLM's Deep Research agent
- **Notebooks**: List, create, rename, delete, and summarize notebooks
- **Sources**: Add URLs, raw text, or local files (PDFs, docs, audio, images); list, inspect, and delete
- **Grounded Q&A**: Ask questions with citations; use `source_ids` for surgical source selection; thread `conversation_id` for follow-ups
- **Chat configuration**: Preset modes (`learning_guide`, `concise`, `detailed`) or custom personas
- **Artifact generation**: Audio overviews, videos, slide decks, mind maps, infographics, quizzes, flashcards, briefing docs / study guides / blog posts, and data tables — all with explicit format/length/style controls
- **Async lifecycle**: List artifacts, check status, wait (capped) for completion, download to local files
- **Safety**: Download and file-upload paths are constrained to `$HOME` by default

---

## Prerequisites

### 1. Install uv (Python Package Manager)

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew (macOS)
brew install uv
```

Default install location: `~/.local/bin/uv`

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
# Using PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with Scoop
scoop install uv

# Or with winget
winget install --id=astral-sh.uv -e
```

Default install location: `%USERPROFILE%\.local\bin\uv.exe`

</details>

Verify installation:
```bash
uv --version
```

### 2. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/alfredang/notebooklm-mcp.git

# Navigate to the project folder
cd notebooklm-mcp

# Install dependencies (includes notebooklm-py and fastmcp)
uv sync
```

This will:
- Create a `.venv` virtual environment
- Install **notebooklm-py** (Python client for NotebookLM API)
- Install **fastmcp** (MCP server framework)

> **Note:** These dependencies are required for both Claude Desktop and Claude Code.

---

## Step 1: Authenticate with NotebookLM

NotebookLM uses browser-based authentication. You must login once to save your session cookies.

```bash
cd notebooklm-mcp
uv run notebooklm login
```

**What happens:**
1. A browser window will open automatically
2. Log in to your Google account
3. Navigate to NotebookLM if not redirected automatically
4. Wait until the terminal displays **"Success"**
5. Close the browser

**Verify authentication:**
```bash
uv run python -c "
from notebooklm import NotebookLMClient
import asyncio
async def test():
    client = await NotebookLMClient.from_storage()
    async with client:
        notebooks = await client.notebooks.list()
        print(f'Authenticated! Found {len(notebooks)} notebooks.')
asyncio.run(test())
"
```

You should see: `Authenticated! Found X notebooks.`

---

## Step 2: Test the MCP Server

Before configuring Claude, verify the server starts correctly:

```bash
cd notebooklm-mcp
uv run python server.py
```

**Expected output:**
```
Starting NotebookLM MCP server...
NotebookLM client initialized successfully
Starting MCP server 'NotebookLM' with transport 'stdio'
```

Press `Ctrl+C` (or `Cmd+C` on Mac) to stop the server after confirming it works.

---

## Step 3: Setup for Claude Desktop

### 3.1 Find Your Paths

You'll need two paths for the configuration:

**Find your `uv` path:**

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
which uv
```
Example output: `/Users/yourname/.local/bin/uv`

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
where uv
```
Example output: `C:\Users\yourname\.local\bin\uv.exe`

</details>

**Find your project path:**

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
cd notebooklm-mcp && pwd
```
Example output: `/Users/yourname/projects/notebooklm-mcp`

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
cd notebooklm-mcp; (Get-Location).Path
```
Example output: `C:\Users\yourname\projects\notebooklm-mcp`

</details>

### 3.2 Open the Config File

**From Claude Desktop (Recommended):**

1. Open Claude Desktop
2. Go to **Settings** (gear icon) → **Developer** → **Edit Config**
3. This opens `claude_desktop_config.json` in your default editor

**Or manually:**

<details>
<summary>macOS path</summary>

`~/Library/Application Support/Claude/claude_desktop_config.json`

</details>

<details>
<summary>Windows path</summary>

`%APPDATA%\Claude\claude_desktop_config.json`

</details>

### 3.3 Add the MCP Server Configuration

> **Important:** Replace `<UV_PATH>` and `<PROJECT_PATH>` with your actual paths from Step 3.1

<details>
<summary><strong>macOS / Linux Configuration</strong></summary>

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "<UV_PATH>",
      "args": [
        "--directory",
        "<PROJECT_PATH>",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

**Example with real paths:**
```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "/Users/yourname/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/yourname/projects/notebooklm-mcp",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

</details>

<details>
<summary><strong>Windows Configuration</strong></summary>

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "<UV_PATH>",
      "args": [
        "--directory",
        "<PROJECT_PATH>",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

**Example with real paths:**
```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "C:\\Users\\yourname\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\Users\\yourname\\projects\\notebooklm-mcp",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

> **Note:** On Windows, use double backslashes (`\\`) in JSON paths.

</details>

### 3.4 Restart Claude Desktop

| Platform | How to Restart |
|----------|----------------|
| **macOS** | Press `Cmd+Q` to fully quit, then reopen |
| **Windows** | Right-click tray icon → Quit, then reopen |

Look for the **hammer icon** in the chat input area - this indicates MCP tools are available.

### 3.5 Verify Connection

In Claude Desktop, type:
```
List my NotebookLM notebooks
```

Claude should use the `list_notebooks` tool and display your notebooks.

---

## Step 4: Setup for Claude Code (CLI)

> **Prerequisites:** Complete Steps 1-2 first (install dependencies with `uv sync` and authenticate with `uv run notebooklm login`).

### 4.1 Add the MCP Server

Replace `<PROJECT_PATH>` with your actual project path:

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
claude mcp add notebooklm -- uv --directory <PROJECT_PATH> run python server.py
```

**Example:**
```bash
claude mcp add notebooklm -- uv --directory /Users/yourname/projects/notebooklm-mcp run python server.py
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
claude mcp add notebooklm -- uv --directory <PROJECT_PATH> run python server.py
```

**Example:**
```powershell
claude mcp add notebooklm -- uv --directory C:\Users\yourname\projects\notebooklm-mcp run python server.py
```

</details>

### 4.2 Verify the Server is Added

```bash
claude mcp list
```

You should see `notebooklm` in the list.

### 4.3 Test in Claude Code

Start a new Claude Code session:
```bash
claude
```

Then ask:
```
List my NotebookLM notebooks
```

---

## Usage Examples

Once configured, use natural language commands in Claude Desktop or Claude Code:

| Task | Example Command |
|------|-----------------|
| List notebooks | "Show me all my NotebookLM notebooks" |
| Create notebook | "Create a new notebook called 'Research Project'" |
| Add URL source | "Add this URL to my notebook: https://example.com/article" |
| Generate podcast | "Generate a podcast for notebook ID xyz123" |
| Create slides | "Make a slide deck from my 'Research Project' notebook" |
| Generate mind map | "Create a mind map for notebook abc456" |
| Create quiz | "Generate a quiz based on my notebook sources" |
| Make flashcards | "Create study flashcards from this notebook" |

---

## Available Tools

The server exposes **39 tools** across six categories. For best-practice usage (prompt templates, source-curation strategies, end-to-end workflows), install the companion skill at `~/.claude/skills/notebooklm-mcp/` — see [Claude Code skill](#claude-code-skill) below.

### Notebooks
| Tool | Description |
|------|-------------|
| `list_notebooks` | List every notebook in your account |
| `create_notebook` | Create a new notebook |
| `get_notebook_summary` | Get the NotebookLM-generated summary |
| `rename_notebook` | Rename an existing notebook |
| `delete_notebook` | Delete a notebook (destructive) |

### Sources
| Tool | Description |
|------|-------------|
| `add_source_url` | Add a URL (web, YouTube, Google Doc, etc.); `wait=True` by default |
| `add_source_text` | Add pasted text as a source |
| `add_source_file` | Upload a local file (PDF, docx, pptx, audio, image) — path must be inside `$HOME` |
| `list_sources` | List every source in a notebook (needed for surgical `source_ids` queries) |
| `get_source_fulltext` | Fetch the indexed text of a single source |
| `delete_source` | Remove a source (destructive) |

### Deep Research
| Tool | Description |
|------|-------------|
| `start_deep_research` | Kick off Deep Research (`mode="deep"` or `"fast"`, `source="web"` or `"drive"`) |
| `check_research_status` | Poll status; pass `import_top_k` to import top sources when `completed` |

### Chat / Q&A
| Tool | Description |
|------|-------------|
| `ask_notebook` | Ask a grounded, cited question; supports `source_ids` and `conversation_id` |
| `set_chat_mode` | Apply a preset mode: `default`, `learning_guide`, `concise`, `detailed` |
| `configure_chat` | Low-level: custom persona, response length, goal |

### Artifact generation
| Tool | Description |
|------|-------------|
| `generate_audio_overview` | Podcast-style deep dive (`audio_format`, `audio_length`) |
| `generate_video_overview` | Video overview (`video_format`, `video_style`) |
| `generate_slide_deck` | Slide deck (`slide_format`, `slide_length`) |
| `generate_mind_map` | Mind map (synchronous — returns JSON inline) |
| `generate_infographic` | Infographic (`orientation`, `detail_level`) |
| `generate_quiz` | Quiz (`difficulty`, `quantity`) |
| `generate_flashcards` | Flashcards (`difficulty`, `quantity`) |
| `generate_summary_report` | Report (`report_format`: `briefing_doc`, `study_guide`, `blog_post`, `custom`) |
| `generate_data_table` | Data table (requires explicit `instructions` describing columns) |

### Artifact lifecycle + downloads
| Tool | Description |
|------|-------------|
| `list_artifacts` | List artifacts in a notebook, optionally filtered by type |
| `check_artifact_status` | Instant status poll for a given task id |
| `wait_for_artifact` | Block (capped at 120s default, 300s hard ceiling) for completion |
| `download_audio_artifact` | Download audio to `.mp3` |
| `download_video_artifact` | Download video to `.mp4` |
| `download_slide_deck_artifact` | Download slides to `.pdf` |
| `download_infographic_artifact` | Download infographic to `.png` |
| `download_report_artifact` | Download report to `.md` |
| `download_data_table_artifact` | Download table to `.csv` |
| `download_mind_map_artifact` | Download mind map JSON |
| `download_quiz_artifact` | Download quiz as `json` / `markdown` / `html` |
| `download_flashcards_artifact` | Download flashcards as `json` / `markdown` / `html` |

### Settings
| Tool | Description |
|------|-------------|
| `set_output_language` | **GLOBAL** — sets output language for all future generations in your account |
| `get_output_language` | Read the current global language code |

### Path safety
`add_source_file` and every `download_*_artifact` tool reject paths outside `$HOME`. To allow other paths (e.g. `/tmp` in CI), set `NOTEBOOKLM_MCP_ALLOW_ROOT=1` in the server environment.

### Claude Code skill
A companion skill that teaches Claude the power-user workflow (Deep Research prompts, 3-step source validation, surgical source selection, async generation etiquette) is at [`~/.claude/skills/notebooklm-mcp/`](https://claude.com/claude-code). The skill auto-loads when users ask for research, literature review, or content generation from a notebook.

### Restarting after a server update
Claude Desktop and Claude Code cache each MCP server's tool schemas at connect time. After updating this server (adding/renaming/removing tools), **fully restart Claude** so the new schemas are discovered. Otherwise the client will still see the old tool list.

---

## Troubleshooting

### "Server disconnected" or "Failed to spawn process"

**Cause**: Claude Desktop can't find `uv` because it doesn't inherit your shell's PATH.

**Solution**: Use the **full absolute path** to `uv` in the config (see Step 3.1).

---

### "Command not found: uv"

<details>
<summary><strong>macOS / Linux</strong></summary>

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

</details>

<details>
<summary><strong>Windows</strong></summary>

Add to your PATH:
1. Open System Properties → Environment Variables
2. Under "User variables", edit `Path`
3. Add: `%USERPROFILE%\.local\bin`
4. Restart your terminal

</details>

---

### MCP Server Not Appearing in Claude Desktop

**Cause**: Invalid JSON in config file or Claude not restarted properly.

**Solution**:
1. Validate your JSON at https://jsonlint.com/
2. Ensure no trailing commas in the JSON
3. Fully quit and reopen Claude Desktop

---

### "NotebookLM client not initialized"

**Cause**: Server started before authentication was complete.

**Solution**:
1. Run `uv run notebooklm login` first
2. Restart Claude Desktop or re-add the MCP server in Claude Code

---

### Check Claude Desktop Logs

<details>
<summary><strong>macOS</strong></summary>

```bash
# View recent logs
tail -100 ~/Library/Logs/Claude/mcp*.log

# Or open in Finder
open ~/Library/Logs/Claude/
```

</details>

<details>
<summary><strong>Windows</strong></summary>

```powershell
# View logs folder
explorer "$env:APPDATA\Claude\logs"
```

</details>

---

### Remove and Re-add MCP Server (Claude Code)

If issues persist:
```bash
claude mcp remove notebooklm
claude mcp add notebooklm -- uv --directory <PROJECT_PATH> run python server.py
```

---

## Updating

To update the NotebookLM library:
```bash
cd notebooklm-mcp
uv sync --upgrade
```

---

## Project Structure

```
notebooklm-mcp/
├── server.py          # Entry point: imports _runtime and tool modules, runs mcp
├── _runtime.py        # Shared FastMCP instance, lifespan, and client singleton
├── enums.py           # Literal ↔ notebooklm-py enum maps for tool parameters
├── errors.py          # @tool_errors decorator + validate_path safety guard
├── tools/
│   ├── __init__.py
│   ├── notebooks.py   # list/create/rename/delete/get_summary
│   ├── sources.py     # add_url/text/file, list, fulltext, delete
│   ├── research.py    # start_deep_research, check_research_status
│   ├── chat.py        # ask_notebook, set_chat_mode, configure_chat
│   ├── artifacts.py   # 9 generators, lifecycle, 9 downloads
│   └── settings.py    # global language settings
├── pyproject.toml     # Project dependencies
├── README.md          # This file
└── .venv/             # Virtual environment (auto-created)
```

---

## License

MIT License
