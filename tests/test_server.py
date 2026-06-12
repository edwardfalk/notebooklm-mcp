"""Server smoke test: importing server.py registers exactly the expected tools."""

from __future__ import annotations

import asyncio

EXPECTED_TOOLS = {
    # notebooks
    "list_notebooks",
    "create_notebook",
    "get_notebook_summary",
    "rename_notebook",
    "delete_notebook",
    # sources
    "add_source_url",
    "add_source_text",
    "add_source_file",
    "list_sources",
    "get_source_fulltext",
    "delete_source",
    # research
    "start_deep_research",
    "check_research_status",
    # chat
    "ask_notebook",
    "set_chat_mode",
    "configure_chat",
    # artifacts: generators
    "generate_audio_overview",
    "generate_video_overview",
    "generate_slide_deck",
    "generate_mind_map",
    "generate_infographic",
    "generate_quiz",
    "generate_flashcards",
    "generate_summary_report",
    "generate_data_table",
    # artifacts: lifecycle
    "list_artifacts",
    "check_artifact_status",
    "wait_for_artifact",
    # artifacts: downloads
    "download_audio_artifact",
    "download_video_artifact",
    "download_slide_deck_artifact",
    "download_infographic_artifact",
    "download_report_artifact",
    "download_data_table_artifact",
    "download_mind_map_artifact",
    "download_quiz_artifact",
    "download_flashcards_artifact",
    # settings
    "set_output_language",
    "get_output_language",
}


def test_all_tools_registered():
    # Importing server triggers every @mcp.tool() decorator; the lifespan
    # (and thus the NotebookLM login) only runs on mcp.run(), so this is
    # safe without credentials.
    import server

    registered = set(asyncio.run(server.mcp.get_tools()))
    assert registered == EXPECTED_TOOLS


def test_get_client_raises_before_lifespan():
    from _runtime import get_client

    try:
        get_client()
    except RuntimeError as exc:
        assert "notebooklm login" in str(exc)
    else:
        raise AssertionError("get_client() should raise before the lifespan runs")
