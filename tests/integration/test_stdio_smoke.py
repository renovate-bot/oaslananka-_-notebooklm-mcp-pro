import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def test_stdio_server_initializes_and_lists_core_tools() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    python_lib_path = str(Path(sys.base_prefix) / "lib")
    existing_library_path = env.get("LD_LIBRARY_PATH")
    if existing_library_path:
        env["LD_LIBRARY_PATH"] = f"{python_lib_path}:{existing_library_path}"
    else:
        env["LD_LIBRARY_PATH"] = python_lib_path
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "nlm_mcp", "stdio"],
        cwd=repo_root,
        env=env,
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=10)
        tools = await asyncio.wait_for(session.list_tools(), timeout=10)
        resources = await asyncio.wait_for(session.list_resources(), timeout=10)
        resource_templates = await asyncio.wait_for(session.list_resource_templates(), timeout=10)
        prompts = await asyncio.wait_for(session.list_prompts(), timeout=10)

    tool_names = {tool.name for tool in tools.tools}
    assert {
        "admin_health",
        "admin_version",
        "notebook_list",
        "notebook_create",
        "notebook_get",
        "notebook_rename",
        "notebook_delete",
        "notebook_share_public",
        "notebook_share_invite",
        "notebook_share_status",
        "source_add_url",
        "source_add_youtube",
        "source_add_file",
        "source_add_gdrive",
        "source_add_text",
        "source_list",
        "source_get",
        "source_get_fulltext",
        "source_refresh",
        "source_wait",
        "source_remove",
        "chat_ask",
        "chat_query",
        "chat_stream_query",
        "chat_conversation_start",
        "chat_continue",
        "chat_history",
        "chat_save_note",
        "chat_list_notes",
        "chat_save_to_notes",
        "research_web_start",
        "research_drive_start",
        "research_status",
        "research_wait",
        "generate_audio_overview",
        "generate_video_overview",
        "generate_cinematic_video",
        "generate_slide_deck",
        "generate_infographic",
        "generate_quiz",
        "generate_flashcards",
        "generate_report",
        "generate_data_table",
        "generate_mind_map",
        "artifact_status",
        "artifact_wait",
        "artifact_list",
        "artifact_download",
        "artifact_delete",
        "artifact_cancel",
        "artifact_revise_slide",
        "language_list",
        "language_get",
        "language_set",
        "search",
        "fetch",
    }.issubset(tool_names)
    assert {str(resource.uri) for resource in resources.resources} == {"notebooklm://notebooks"}
    assert {template.uriTemplate for template in resource_templates.resourceTemplates} == {
        "notebooklm://notebook/{id}",
        "notebooklm://notebook/{id}/source/{src_id}",
        "notebooklm://notebook/{id}/source/{src_id}/fulltext",
        "notebooklm://notebook/{id}/mindmap",
        "notebooklm://artifact/{task_id}",
    }
    assert {prompt.name for prompt in prompts.prompts} == {
        "summarize-research",
        "study-pack",
        "meeting-to-podcast",
        "paper-deep-dive",
    }
