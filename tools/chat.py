"""Chat / Q&A MCP tools."""

from __future__ import annotations

from notebooklm.types import ChatMode

from _runtime import get_client, mcp
from enums import (
    CHAT_GOAL_MAP,
    CHAT_RESPONSE_LENGTH_MAP,
    ChatGoalLiteral,
    ChatModeLiteral,
    ChatResponseLengthLiteral,
    lookup_enum,
)
from errors import tool_errors


@mcp.tool()
@tool_errors
async def ask_notebook(
    notebook_id: str,
    question: str,
    source_ids: list[str] | None = None,
    conversation_id: str | None = None,
) -> dict:
    """Ask a question grounded in a notebook's sources, with citations.

    **Surgical source selection** (the key Medium-article technique): pass
    ``source_ids=[...]`` to restrict the answer to a specific subset of the
    notebook's sources instead of all of them. This is how you get focused,
    non-generic answers — leave every source checked and NotebookLM averages
    everything together into mush. Use ``list_sources`` to find the ids.

    **Follow-ups**: the returned ``conversation_id`` can be threaded back
    into a subsequent call so NotebookLM knows this is a continuation. Use
    this for drill-down Q&A within a single conversation thread. Omit
    ``conversation_id`` to start a fresh conversation.

    **Citations**: the ``references`` list contains source-backed citations
    with ``citation_number``, ``cited_text``, and ``source_id``. Always
    surface these when relaying the answer to the user — never paraphrase
    without citing.

    **Anti-pattern**: don't use this for things the model already knows or
    for real-time data. Deep Research and grounded Q&A only make sense when
    the answer is meant to come from the notebook's specific sources.
    """
    client = get_client()
    result = await client.chat.ask(
        notebook_id,
        question,
        source_ids=source_ids,
        conversation_id=conversation_id,
    )
    return {
        "answer": result.answer,
        "conversation_id": result.conversation_id,
        "turn_number": result.turn_number,
        "is_follow_up": result.is_follow_up,
        "references": [
            {
                "citation_number": r.citation_number,
                "cited_text": r.cited_text,
                "source_id": r.source_id,
            }
            for r in result.references
        ],
    }


@mcp.tool()
@tool_errors
async def set_chat_mode(notebook_id: str, mode: ChatModeLiteral) -> dict:
    """Apply a pre-built chat mode to a notebook (the 90% ergonomic case).

    Four modes are available:

    - ``"default"`` — general-purpose research and brainstorming.
    - ``"learning_guide"`` — educational focus, ideal for study/exam prep.
    - ``"concise"`` — brief, to-the-point answers. Use before generating
      briefing docs or when the user wants executive-summary answers.
    - ``"detailed"`` — verbose, thorough synthesis. Use for literature
      review or when the user wants depth.

    Choose a mode **before** asking questions or generating artifacts — it
    affects both. For anything more custom (e.g. setting a persona prompt),
    use ``configure_chat`` instead.
    """
    client = get_client()
    await client.chat.set_mode(notebook_id, ChatMode(mode))
    return {"notebook_id": notebook_id, "mode": mode, "applied": True}


@mcp.tool()
@tool_errors
async def configure_chat(
    notebook_id: str,
    goal: ChatGoalLiteral | None = None,
    response_length: ChatResponseLengthLiteral | None = None,
    custom_prompt: str | None = None,
) -> dict:
    """Low-level chat configuration (custom persona, response length).

    Prefer ``set_chat_mode`` unless you specifically need a custom persona.

    - ``goal="custom"`` requires ``custom_prompt`` (up to ~10,000 chars)
      describing the persona or perspective NotebookLM should adopt, e.g.
      ``"You are a research analyst focused on AI safety and alignment
      debates. Prioritize empirical findings over opinion."``
    - ``goal="learning_guide"`` is the same as ``set_chat_mode("learning_guide")``.
    - ``response_length`` accepts ``"default"``, ``"longer"``, or ``"shorter"``.
    """
    client = get_client()
    await client.chat.configure(
        notebook_id,
        goal=lookup_enum("goal", goal, CHAT_GOAL_MAP),
        response_length=lookup_enum(
            "response_length", response_length, CHAT_RESPONSE_LENGTH_MAP
        ),
        custom_prompt=custom_prompt,
    )
    return {
        "notebook_id": notebook_id,
        "goal": goal,
        "response_length": response_length,
        "has_custom_prompt": custom_prompt is not None,
        "configured": True,
    }
