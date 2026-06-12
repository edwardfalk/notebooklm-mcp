# Tool Review — are all 39 tools earning their keep?

*Reviewed 2026-06-12 after a full E2E test (28/39 tools exercised live) and a
NotebookLM Deep Research pass on current MCP tool-design best practice.*

## Measurements

- **39 tools, 27,376 schema chars ≈ 6,850 tokens** if a client loads them all.
- Claude Desktop loads all schemas upfront (~3.4% of a 200k context).
- Claude Code **defers MCP schemas via Tool Search** (loads on demand,
  auto-triggers when tool descriptions would exceed 10% of context), so the
  token cost there is near zero until a tool is actually used.
- Heaviest schemas: `generate_audio_overview` (1.8k chars),
  `generate_video_overview` (1.6k), `ask_notebook` (1.5k) — all deliberate,
  the docstrings are doing prompt-engineering work.
- Field guidance (Deep Research, 2026): aim for 5–15 aggressively-curated
  tools per server; consolidate tools that an agent must chain for one
  outcome; keep destructive operations separate for permission granularity.

## Verdict by category

| Category | Tools | Verdict |
|---|---|---|
| Notebooks | 5 | **Keep all.** Distinct operations; `rename_notebook` is marginal but costs 325 chars. |
| Sources | 6 | **Keep all.** The three `add_source_*` differ in inputs and safety surface (file upload has the `$HOME` guard); merging would tangle the schema. |
| Deep Research | 2 | **Keep.** The start/poll+import split matches the async reality. |
| Chat | 3 | **Keep `ask_notebook`.** `set_chat_mode` vs `configure_chat` overlap (mode presets vs custom persona) — merge candidate, tier 2. |
| Generators | 9 | **Keep separate.** Each type has genuinely different option enums (audio_format vs video_style vs orientation...). One mega-tool would need a conditional schema the model would misuse. Exception: `generate_quiz` and `generate_flashcards` have *identical* parameters — merge candidate, tier 2. |
| Lifecycle | 3 | **Keep.** `check_artifact_status` (instant) vs `wait_for_artifact` (capped block) encode the polling etiquette in their names; that distinction prevented loop-waiting during the E2E. |
| Downloads | 9 | **Consolidate → 1** (tier 1, recommended). See below. |
| Settings | 2 | **Keep.** `set_output_language` mutates global account state — exactly the kind of tool that must stay separately deniable. |

## Tier 1 (recommended): consolidate the 9 `download_*` tools into one

`download_artifact(notebook_id, artifact_type, output_path, artifact_id=None,
output_format=None)`

- The nine tools have **identical parameters** (quiz/flashcards add
  `output_format` — fold in as optional, validated per type).
- **Identical permission profile** — they all write one file inside `$HOME`.
  Nothing is lost in allow/deny granularity, which is the one principled
  argument for keeping tools separate.
- The `artifact_type` enum documents legal values exactly as well as nine
  names do, and `list_artifacts` already returns `kind` in the same
  vocabulary — the model can pipe `kind` straight into `artifact_type`.
- Saves 8 tools and ~3,400 schema chars (~850 tokens); 39 → 31.
- Bonus: `download_mind_map_artifact` (whose generate variant already
  returns JSON inline) stops being a standalone oddity.

## Tier 2 (optional, weaker wins)

1. **`generate_quiz` + `generate_flashcards` → `generate_study_material(kind=...)`**
   — identical params today; the separate names do map well to user intent,
   so this trades a little clarity for one less tool. 31 → 30.
2. **`set_chat_mode` folded into `configure_chat`** as a `mode` parameter —
   the preset path is the documented 90% case, so if merged, the combined
   docstring must keep presets front and center. 30 → 29.

## Tier 3 (not recommended now)

- **Docstring slimming**: the long generator docstrings (~40% of total schema
  bytes) duplicate guidance that also lives in the companion skill. Trimming
  would save ~2k tokens in Claude Desktop, but the docstrings are what make
  the server usable from clients *without* the skill. Revisit only if
  Desktop context pressure becomes real.
- **Tool-count crusade below ~30**: the 5–15 guidance assumes single-job
  servers; this server deliberately wraps a whole product. With Claude
  Code deferring schemas, further consolidation buys little.

## Bottom line

The catalog is in good shape: every tool was designed against a real
operation, the heavyweight docstrings are doing useful prompting work, and
28/39 tools survived live testing without a single wrong-tool-choice moment.
The one structural improvement worth making is the **download consolidation
(39 → 31)**; everything else is taste.
