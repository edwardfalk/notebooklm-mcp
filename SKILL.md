---
name: notebooklm-mcp
description: Use the notebooklm MCP server whenever a task benefits from source-grounded, citation-backed research — deep web investigation of a topic, literature synthesis from a curated corpus, defensible Q&A with citations against specific documents, structured data extraction across sources, or producing research deliverables (audio overview, video, slide deck, infographic, briefing doc, study guide, mind map, quiz, flashcards, data table) from a notebook. Reach for this proactively on research, comparison, and synthesis tasks where answers should be traceable to specific sources — not just when the user explicitly asks for a notebook or a podcast.
---

# NotebookLM MCP — Research Partner for Claude

## 1. What NotebookLM Is

Google Labs' **source-grounded AI research partner**. Every answer it gives comes **exclusively** from sources *you* curated, with clickable citation chips that trace each claim back to a specific passage in the original document.

- **Engine:** Gemini 3, with a **1M-token context window per source** (as of March 2026). You can hand it a book-length PDF without chunking.
- **Closed RAG, not open retrieval:** NotebookLM has no web access during chat. Deep Research is the single exception — it crawls the web *once* to build a corpus, then the notebook stays closed-world from then on.
- **It says "I don't know" before it hallucinates.** This is a feature, not a bug.
- **Accepts:** PDFs, DOCX, Google Docs/Slides/Drive, web pages, YouTube (via transcripts), text/markdown, CSV, images (OCR), audio, video.
- **Produces:** grounded Q&A, Deep Research reports, and nine artifact types — audio overview (podcast-style), video overview, slide deck, mind map, infographic, quiz, flashcards, summary report, data table.

## 2. Mental Model: The Tradeoff

- **General LLMs trade accuracy for breadth.** They answer anything, sometimes incorrectly.
- **NotebookLM trades breadth for accuracy.** It only answers from the sources you handed it — but when it answers, every claim is verifiable in one click.
- This is **complementary** to Claude's own reasoning, not a replacement. Use it when defensibility matters more than speed.
- **Rule of thumb:** if the user will ever ask *"where did you get that,"* reach for NotebookLM.

## 3. When to Reach for This (Proactively)

**Autonomy policy.** Claude has **free rein** on non-destructive operations via this MCP. Claude may autonomously create notebooks, add sources, run Deep Research, ask questions, and generate any artifact it judges useful — without asking first. The only tools that require user confirmation are the three in Section 10 (destructive or globally-scoped).

### 3a. Reach for this MCP on:

- **Research synthesis on an unfamiliar or fast-moving topic.** *"What's the current state of X?"*, *"I want to understand Y as of 2026."* → create a notebook and run Deep Research.
- **Any question where citation or traceability matters.** Legal, regulatory, medical, or academic claims. *"Does this paper say X?"*, *"According to the Smith 2025 report..."* → `ask_notebook` with `source_ids`.
- **Comparison or contrast across a body of documents.** *"Compare these three proposals,"* *"what do these authors disagree about,"* *"what's missing from the X literature?"* → surgical source selection in `ask_notebook`.
- **Briefing or executive-summary production from multiple sources.** *"Summarize everything we've collected about X,"* *"I need a one-pager on this."* → `generate_summary_report` with `report_format="briefing_doc"`.
- **Verbatim quotation retrieval.** *"What exactly does the paper say about X?"* → `get_source_fulltext`, not paraphrase.
- **Structured data extraction across sources.** *"Pull every effect size from these studies,"* *"build a chronology from these historical sources."* → `generate_data_table` with explicit column instructions.
- **Check for existing prior research first.** Before starting fresh work, call `list_notebooks` and `get_notebook_summary` — the user may already have a notebook you can build on.
- **User-requested deliverables.** *"Make a podcast,"* *"turn this into a slide deck,"* *"I want an infographic."* → generate and download the requested artifact.

### 3b. Do NOT use this for:

- **Things already in Claude's training** — foundational topics, stable scientific facts, well-known algorithms, textbook material. Wastes round-trips and tokens.
- **Real-time data** — stock prices, live news, breaking events, weather. Notebooks are snapshots; only Deep Research is fresh, and only at the moment it ran.
- **Code execution or debugging** — this is a research tool, not an interpreter. Use Bash.
- **Single-document tasks without citation needs.** If the user hands Claude one file and asks for a summary, Claude's own long context is faster than uploading to NotebookLM. Reach for this on *multi-source* synthesis, not single-file work.
- **Private or sensitive data the user has not authorized for Google upload.** Proprietary code, unreleased docs, PII. Ask first — NotebookLM is a Google product.
- **When the user explicitly wants Claude's own opinion or reasoning.** NotebookLM refuses to go beyond its sources, which is the opposite of what the user asked for.
- **Generative image or video requests untethered to sources.** NotebookLM's visual outputs are always *about* a corpus, not arbitrary prompts.

## 4. The Research Workflow

Claude walks a research task through five phases: **Scope → Assemble → Interrogate → Distill → Deliver**. Each phase maps to a cluster of MCP tools.

### Phase 1: Scope the work

- **First question: is this already in a notebook?** Call `list_notebooks` before creating anything new. The user may have prior research Claude can build on.
- **Second question: one notebook per research question.** Do not mix unrelated topics into one notebook — it dilutes retrieval quality and confuses the chat model.
- **Naming convention: outcome + timeframe.** Good: `"AI alignment frontier models 2026"`, `"GDPR article 22 case law 2020-2025"`. Bad: `"research"`, `"notes"`, `"new stuff"`.
- **Reuse threshold.** If an existing notebook's topic is within ~10% of the new question and it has fewer than ~30 sources, reuse it. Otherwise create fresh — citation specificity starts degrading before you hit the 50-source cap.
- **Inspect before reusing.** Call `get_notebook_summary` to see the notebook's auto-generated summary before deciding to reuse it.
- **Cleanup etiquette.** If the user is close to the 100-notebook ceiling, offer to remove old throwaway notebooks — but **confirm first** (see Section 10).
- **Tools:** `list_notebooks`, `get_notebook_summary`, `create_notebook`, `rename_notebook`, `delete_notebook` (confirm first).

### Phase 2: Assemble the corpus

- **The quality of every downstream answer is bounded by the corpus.** Spend real effort here.
- **Three ways to add sources.** `add_source_url` for web pages, YouTube, and Google Docs. `add_source_text` for pasted content or transcripts. `add_source_file` for local files (PDF, DOCX, PPTX, MD, TXT, audio, video).
- **Default `wait=True` blocks until indexing completes.** A source must be `ready` before `ask_notebook` or any `generate_*` tool can use it. Do not set `wait=False` unless you are polling separately.
- **File paths must be absolute and inside `$HOME`** (see Section 9). If the user needs a file in `/tmp` or elsewhere, ask them to move it or explain the restriction.
- **URL sources are not always reliable.** Paywalled articles, JavaScript-heavy SPAs, and login-gated pages sometimes index as empty or malformed. After adding, call `list_sources` and sanity-check the `status` field. If something looks wrong, call `get_source_fulltext` to see what NotebookLM actually captured, and re-add in a different format if necessary.
- **Three-step source validation** (field-tested pattern): (1) add the source, (2) call `list_sources` to confirm `status == "ready"`, (3) spot-check with `get_source_fulltext` or a test `ask_notebook` query. This catches indexing failures before you waste a generation on them.
- **Source ceiling: 50 per notebook.** If you are close to the cap, delete unused sources first.
- **Deep Research auto-adds sources.** Don't hand-curate when a Deep Research run would find and import the top-N for you — see Section 5.
- **Tools:** `add_source_url`, `add_source_text`, `add_source_file`, `list_sources`, `get_source_fulltext`, `delete_source` (confirm first).

### Phase 3: Interrogate with grounded Q&A

This is the most behavior-critical phase. Most of the value of this MCP is concentrated here.

- **`ask_notebook` is the workhorse.** Prefer it over Claude's own reasoning whenever the answer is supposed to come from the sources.
- **Surgical source selection is THE power move.** Left to its own devices, NotebookLM averages across every source in the notebook and produces mushy generic answers. Always: call `list_sources` first, pick the 2–6 sources most relevant to the current question, and pass them as `source_ids=[...]`. This single parameter is the difference between a useful answer and a worthless one.
- **Citations are mandatory, not optional.** The `references` list on every `ask_notebook` response contains `citation_number`, `cited_text`, and `source_id`. When Claude relays the answer to the user, **always surface these citations**. Never paraphrase NotebookLM's answer without attribution — paraphrasing without citation destroys the entire value proposition of this tool and defeats the reason to use it over Claude's own reasoning.
- **Conversation threading.** The response also includes a `conversation_id`. Pass it back on the next `ask_notebook` call to continue the same thread (useful for drill-down follow-ups: *"What did you mean by X in your last answer?"*). Omit it to start fresh.
- **Chat modes** (via `set_chat_mode`):
  - `default` — general research and brainstorming.
  - `learning_guide` — educational framing, for study and exam prep. Pair with `generate_flashcards` or `generate_quiz`.
  - `concise` — brief, to-the-point answers. Pair with `generate_summary_report(report_format="briefing_doc")` for executive outputs.
  - `detailed` — verbose synthesis. For literature review.
  - Call `set_chat_mode` **before** asking questions or generating artifacts — it affects both.
- **Custom personas** via `configure_chat(goal="custom", custom_prompt=...)` when a preset does not fit. Example persona: *"You are a research analyst focused on AI safety and alignment debates. Prioritize empirical findings over opinion."* Custom prompt limit is ~10,000 characters.
- **Query construction:**
  - Ask for a specific claim plus supporting evidence, not a generic topic sweep.
  - Ask the question you would ask a subject-matter expert with the full corpus in front of them — not the question you would type into Google.
  - If the answer comes back too vague, **narrow the `source_ids`** rather than rephrasing the question.
- **Anti-patterns.** Asking about things in Claude's training, asking about real-time data, asking single-source questions that don't need citation. None of these justify the round-trip.
- **Tools:** `ask_notebook`, `set_chat_mode`, `configure_chat`, `list_sources` (for source selection), `get_source_fulltext` (for verbatim quoting).

### Phase 4: Distill into written synthesis

Turn interrogation into durable deliverables Claude uses as its own working output.

- **`generate_summary_report`** — four `report_format` values:
  - `briefing_doc` (default) — executive briefing. The right default for most synthesis work.
  - `study_guide` — educational breakdown with sections and review questions.
  - `blog_post` — long-form write-up.
  - `custom` — **requires `custom_prompt`** describing the exact shape of the report you want. Use this when none of the three presets fit.
- **`generate_data_table`** is underused. Unlike other generators, its `instructions` parameter is **required** — you must describe the columns explicitly. Good for extracting study metadata from a pile of papers, pulling pricing across vendor pages, or building chronologies from historical sources. Example: *"Make a table of every study mentioned with columns: author, year, sample size, finding, effect size, and the source id it came from."*
- **Surgical source selection applies here too.** Pass `source_ids` to restrict the report or table to specific sources for a focused synthesis.
- **Why this phase is separate from Phase 5.** Reports and data tables are Claude's own working output — intermediate artifacts Claude uses to reason over a corpus. Audio, video, slides, and infographics in Phase 5 are more public-facing deliverables for the user.
- **Tools:** `generate_summary_report`, `generate_data_table`, plus the async lifecycle tools from Section 7.

### Phase 5: Deliver user-facing artifacts

- **Free rein.** Claude may generate any of these autonomously when useful for the task — no pre-ask required. Still, check that a generation is actually worth the minutes it takes (especially video).
- **Seven deliverable types, with when-to-use and control surface:**
  - **`generate_audio_overview`** — podcast-style deep dive. ~1–3 minutes to generate. Formats: `deep_dive` (default), `brief`, `critique`, `debate`. **Use `debate` when sources disagree** — it produces the most interesting output. Lengths: `short`, `default`, `long`.
  - **`generate_video_overview`** — **15–45 minutes** to generate. Formats: `explainer` or `brief`. Nine visual styles: `auto_select`, `classic`, `whiteboard`, `kawaii`, `anime`, `watercolor`, `retro_print`, `heritage`, `paper_craft`. Do NOT block waiting on this (see Section 7).
  - **`generate_slide_deck`** — `presenter_slides` for visual-first live presentation, `detailed_deck` for text-heavy standalone reading. Lengths: `default` or `short`.
  - **`generate_mind_map`** — **synchronous**. Returns the mind-map JSON inline immediately. Do NOT route its return value through `wait_for_artifact` — there is no task to wait on (see Section 7).
  - **`generate_infographic`** — **field-tested defaults: `orientation="landscape"` and `detail_level="standard"`.** `"detailed"` tends to produce text-rendering errors; `"concise"` drops too much context.
  - **`generate_quiz`** / **`generate_flashcards`** — `difficulty` (`easy`/`medium`/`hard`) and `quantity` (`fewer`/`standard`/`more`). For flashcards, run `set_chat_mode("learning_guide")` first for the best educational framing. Neither tool accepts a `language` parameter — both inherit the global setting.
- **Always give explicit instructions.** The default click on any of these is generic. Two sentences of focused guidance is the difference between forgettable and memorable output. Example for audio: *"Focus on the disagreements between AI safety researchers about alignment approaches, keep it under fifteen minutes, and speak like a thoughtful senior engineer."*
- **Surgical source selection applies here too.** A podcast about one paper beats a podcast about the whole notebook.
- **Downloads.** Each artifact type has a matching `download_*_artifact` tool. Paths must be absolute and inside `$HOME`. Extensions: audio → `.mp3`, video → `.mp4`, slides → `.pdf`, infographic → `.png`, report → `.md`, data table → `.csv`, mind map → `.json`, quiz/flashcards → `.json` / `.md` / `.html` (via `output_format`). Parent directories are created automatically.
- **Tools:** the nine `generate_*`, `list_artifacts`, `check_artifact_status`, `wait_for_artifact`, and the nine `download_*_artifact` tools.

## 5. Deep Research: The Flagship Move

Deep Research is NotebookLM's power tool. It sends an agent to crawl the open web (or a Google Drive), finds 30–50 sources for a specific question, evaluates their trustworthiness, and produces a synthesized report — all in 15–30 minutes for `mode="deep"`. This removes the manual corpus-building bottleneck entirely.

**When to use it (proactively).** Any research scenario where the user doesn't already have sources. Whenever Claude would otherwise say *"I'll do a web search and read through articles"* — reach for this instead. The headline use case is precisely the one the user's CLAUDE.md calls out: *"creating a new notebook with Deep Research will automatically scan for sources and evaluate how trustworthy they are."*

### Prompt engineering (the single highest-leverage tip)

**Specificity plus time-bounding beats everything else.** A solid Deep Research prompt includes the outcome you care about, the domain, and the year.

- **Good:** `"AI alignment and safety challenges for frontier models in 2026"`
- **Bad:** `"AI alignment"`

Patterns that work:
- `"[topic] [domain] [year]"` — e.g. `"contrastive learning methods for medical imaging 2024-2026"`
- `"State of [topic] as of [timeframe]"` — e.g. `"State of post-quantum cryptography deployments as of 2026"`
- `"Evidence for/against [claim] since [year]"` — e.g. `"Evidence for and against microplastic health effects in humans since 2020"`

Patterns that fail:
- Single-word topics (`"AI alignment"`) — produces a generic pull.
- Permanently-framed questions (`"what is transformer architecture"`) — Claude already knows this.
- Opinion-shaped questions (`"is decentralized finance good"`) — NotebookLM won't take a side; you'll get mush.

### Mode and source selection

- **`mode="deep"`** (default): 30–50 sources, 15–30+ minutes. Use for broad topics where you want comprehensive coverage.
- **`mode="fast"`**: ~5–10 sources, under 2 minutes. Use for a quick scoping pass or when the topic is already tightly framed.
- **`source="drive"`**: searches the user's Google Drive instead of the open web. **Incompatible with `mode="deep"`** — drive searches are fast only.

### The standard lifecycle loop

Follow this mechanically:

1. `start_deep_research(notebook_id, query="...", mode="deep")` — returns a `task_id` immediately. Non-blocking.
2. Tell the user the expected wait (*"15–30 minutes"*) and yield control if possible.
3. Loop: `check_research_status(notebook_id)` every 30–60 seconds. Do NOT tight-loop.
4. When `status == "completed"`, call `check_research_status(notebook_id, import_top_k=15)` **in a single call** — this both fetches the results *and* imports the top 15 sources into the notebook. No separate import tool needed.
5. The notebook is now populated → proceed to Phase 3 (Interrogate).

### Things that will bite you

- **`status == "no_research"` is NOT an error.** It's a normal resting state meaning nothing is in flight for this notebook. Don't retry or treat it as failure.
- **`import_top_k`: default 10–15** for most questions. More than ~20 dilutes source focus and eats into the 50-source cap. Fewer than 5 defeats the point of Deep Research.
- **Parallel agents collide.** Deep Research state is per-notebook. Two agents running `start_deep_research` on the same notebook will overwrite each other's tasks. Give each agent its own notebook.
- **Don't poll forever.** If a Deep Research run is still in progress when the conversation ends, tell the user how to resume (another `check_research_status` call later) rather than burning tokens tight-polling.

## 6. Parallel-Agent and Multi-Notebook Safety

- **Always pass explicit `notebook_id`** on every call. The MCP has no implicit "current notebook" state — but Claude may imagine one from habit. Don't.
- **`conversation_id` is a hard dependency** for threaded follow-ups. Save it from the `ask_notebook` response and pass it back explicitly on the next call. Do not assume the next call remembers the thread.
- **`set_output_language` is global and account-wide.** Changing it affects every future generation in every notebook, including other concurrent agents'. **Prefer the per-call `language` parameter** on generator tools (`generate_audio_overview`, `generate_video_overview`, `generate_slide_deck`, `generate_infographic`, `generate_summary_report`, `generate_data_table`). See Section 10.
- **Deep Research state is per-notebook.** Parallel agents doing Deep Research need separate notebooks.
- **Pass IDs as full UUIDs** — don't truncate for "readability" in automation paths.

## 7. Async Lifecycle Etiquette

- **Every generator except `generate_mind_map` is asynchronous.** They return `{task_id, artifact_id, status}` immediately without waiting for completion. **Important: `task_id` and `artifact_id` are the same UUID** — the same id serves both roles (polling a running task and referencing the finished artifact). Don't try to map one to the other or treat them as distinct.
- **Three lifecycle tools, ordered by cost:**
  - **`check_artifact_status(notebook_id, task_id)`** — instant single API call. **Use this first** after any `generate_*` call.
  - **`wait_for_artifact(notebook_id, task_id, max_wait_seconds)`** — blocks until completion or until `max_wait_seconds`. Default is 120 seconds; the **hard ceiling is 300 seconds** (silently clamped if you ask for more). If the artifact is still running at the deadline, returns `{"status": "in_progress", "elapsed_seconds": N, "hint": "..."}` — **this is not a failure**. Re-poll with `check_artifact_status` or call `wait_for_artifact` again later.
  - **`list_artifacts(notebook_id, artifact_type=...)`** — enumerate a notebook's artifacts, optionally filtered by type (`audio`, `video`, `slide_deck`, `mind_map`, `infographic`, `quiz`, `flashcards`, `report`, `data_table`). Use when you don't already have the task id.
- **Generation-time expectations** (memorize or you will mis-budget time):
  - Mind map: **synchronous**, returns inline, zero wait.
  - Report / data table: ~30–90 seconds.
  - Quiz / flashcards: ~1–3 minutes.
  - Audio overview: ~1–3 minutes.
  - Slide deck / infographic: ~2–5 minutes.
  - Video overview: **15–45 minutes. Treat as overnight work.**
- **Fire-and-forget pattern for slow generators:**
  1. Kick off the job.
  2. Tell the user the expected wait time.
  3. Call `wait_for_artifact` once with a short `max_wait_seconds` (e.g. 60) to catch fast completions.
  4. If it's still running, yield control to the user. Poll with `check_artifact_status` only when they ask again.
  5. **Never tight-loop `wait_for_artifact` on video.**
- **Mind map exception, stated again because it's a footgun.** `generate_mind_map` is synchronous and returns the JSON inline. Do NOT pass its result through `wait_for_artifact` — there is no task to wait on, and the call will behave unexpectedly.
- **Downloads require completed status.** Trying to `download_*_artifact` on an artifact whose status is still `pending` or `in_progress` will fail. Check with `check_artifact_status` first.

## 8. Error Handling and Retry Decisions

Every tool returns either its normal result or a structured error of shape:

```
{"error": {"type": "...", "message": "...", "retryable": true|false,
           "retry_after_seconds": N (optional), "status_code": N (optional)}}
```

**Retryable** (back off once or twice, not forever):
- `rate_limit` — honor `retry_after_seconds` if present; otherwise wait 30 seconds.
- `timeout`, `network`, `server` — transient infrastructure. Retry with short backoff.
- `source_timeout` — source processing took too long. Re-add or poll manually.
- `artifact_not_ready` — you tried to download too early. Wait, then retry.
- `artifact_download` — transient download failure. Retry.

**Not retryable** (surface to user, don't loop):
- `auth` — session expired. Tell the user to run `uv run notebooklm login` in the project directory. Not auto-recoverable.
- `validation` — Claude passed bad arguments. Re-read the tool's docstring and fix the call.
- `notebook_not_found` / `source_not_found` — list the parent collection (`list_notebooks` or `list_sources`) to find the right id.
- `client`, `source_processing`, `source_add`, `artifact_not_found`, `artifact_parse`, `chat`, `configuration`, `rpc` — report to the user and ask how to proceed.

**Decision rule.** `retryable=true` → back off and retry at most 2 times. `retryable=false` → do not retry, surface to the user.

## 9. Path Safety

- All file operations (`add_source_file` and every `download_*_artifact`) require **absolute paths inside `$HOME`**.
- Paths outside `$HOME` are rejected with a `validation` error unless `NOTEBOOKLM_MCP_ALLOW_ROOT=1` was set in the MCP server's environment at startup.
- Path resolution canonicalizes before validation — symlink tricks and `..` escapes are caught.
- Parent directories are created automatically by `download_*` tools.
- If the user asks for a path outside `$HOME`, explain the restriction and ask them to either move the file into `$HOME` or restart the MCP server with `NOTEBOOKLM_MCP_ALLOW_ROOT=1` set.

## 10. Confirm Before: Destructive and Global Operations

Free rein applies to everything except these three tools. **Always ask the user before calling them.**

- **`delete_notebook`** — irreversible. Wipes the notebook, all its sources, and all generated artifacts. Ask even when the user says *"clean up my notebooks"* — confirm which specific ones.
- **`delete_source`** — irreversible. Ask before removing a source, even when replacing it with a better version.
- **`set_output_language`** — **globally mutates the user's NotebookLM account.** It affects every future generation in every notebook and every concurrent agent. **Prefer the per-call `language` parameter** on generator tools instead (`generate_audio_overview`, `generate_video_overview`, `generate_slide_deck`, `generate_infographic`, `generate_summary_report`, `generate_data_table` — but note `generate_quiz` and `generate_flashcards` have no `language` parameter and fall back to the global). If you absolutely must change the global, capture the current value with `get_output_language` first and offer to restore it after.

Everything else — creating notebooks, adding sources, running Deep Research, asking questions, generating any artifact, downloading to `$HOME` paths — is authorized without asking.

## 11. What This Skill Does NOT Cover

- **The full 39-tool reference table with parameter signatures** — see `README.md` at the project root. This skill is a behavioral guide; the README is the reference manual.
- **Installation and Claude Desktop / Claude Code MCP server configuration** — see the README's "Prerequisites" through "Setup for Claude Code" sections.
- **Troubleshooting** (server disconnect, `uv` not found, log locations) — see the README's "Troubleshooting" section.
- **Project file layout** — see the README's "Project Structure" section.
- **Updating the server** — see the README's "Updating" section.
