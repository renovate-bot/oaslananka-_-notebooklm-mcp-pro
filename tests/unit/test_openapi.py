"""Tests for OpenAPI schema generation."""

from __future__ import annotations

from pydantic import SecretStr
from starlette.testclient import TestClient

from nlm_mcp.cli import _http_app
from nlm_mcp.config import AuthMode, Settings, TransportMode
from nlm_mcp.openapi import OPENAPI_SCHEMA, TOOL_SPECS

HTTP_OK = 200
MIN_OPENAPI_PATHS = 20


EXPECTED_TOOLS = [
    "notebook.list",
    "notebook.create",
    "notebook.get",
    "notebook.rename",
    "notebook.delete",
    "notebook.share_public",
    "notebook.share_invite",
    "notebook.share_status",
    "source.add_url",
    "source.add_youtube",
    "source.add_file",
    "source.add_gdrive",
    "source.add_text",
    "source.list",
    "source.get",
    "source.get_fulltext",
    "source.refresh",
    "source.wait",
    "source.remove",
    "source.delete",
    "chat.ask",
    "chat.query",
    "chat.stream_query",
    "chat.conversation_start",
    "chat.continue",
    "chat.history",
    "chat.save_to_notes",
    "chat.save_note",
    "chat.list_notes",
    "research.web_start",
    "research.drive_start",
    "research.status",
    "research.wait",
    "generate.audio_overview",
    "generate.video_overview",
    "generate.cinematic_video",
    "generate.infographic",
    "generate.slide_deck",
    "generate.report",
    "generate.mind_map",
    "generate.data_table",
    "generate.quiz",
    "generate.flashcards",
    "artifact.list",
    "artifact.status",
    "artifact.wait",
    "artifact.download",
    "artifact.delete",
    "artifact.revise_slide",
    "artifact.cancel",
    "language.list",
    "language.get",
    "language.set",
    "search",
    "fetch",
    "admin.health",
    "admin.version",
]


def test_schema_is_valid_openapi_3_1() -> None:
    assert OPENAPI_SCHEMA["openapi"] == "3.1.0"
    assert "paths" in OPENAPI_SCHEMA
    assert len(OPENAPI_SCHEMA["paths"]) == len(TOOL_SPECS)
    assert len(OPENAPI_SCHEMA["paths"]) > MIN_OPENAPI_PATHS


def test_all_tools_have_openapi_paths() -> None:
    for tool in EXPECTED_TOOLS:
        assert f"/tools/{tool}" in OPENAPI_SCHEMA["paths"], f"Missing path for {tool}"


def test_schema_server_url_templating() -> None:
    settings = Settings(
        transport=TransportMode.HTTP,
        auth_mode=AuthMode.TOKEN,
        bearer_token=SecretStr("token"),
        base_url="https://nlm.example.test/",
    )
    with TestClient(_http_app(settings)) as client:
        response = client.get("/openapi.json")

    assert response.status_code == HTTP_OK
    payload = response.json()
    assert payload["servers"] == [
        {"url": "https://nlm.example.test", "description": "NotebookLM MCP Server"}
    ]
    assert payload["security"] == [{"BearerAuth": []}]


def test_plugin_manifest_uses_auth_mode() -> None:
    settings = Settings(
        transport=TransportMode.HTTP,
        auth_mode=AuthMode.TOKEN,
        bearer_token=SecretStr("token"),
        base_url="https://nlm.example.test",
    )
    with TestClient(_http_app(settings)) as client:
        response = client.get("/.well-known/ai-plugin.json")

    assert response.status_code == HTTP_OK
    manifest = response.json()
    assert manifest["auth"] == {"type": "service_http", "authorization_type": "bearer"}
    assert manifest["api"]["url"] == "https://nlm.example.test/openapi.json"


def test_oauth_metadata_endpoints() -> None:
    settings = Settings(
        transport=TransportMode.HTTP,
        auth_mode=AuthMode.NONE,
        base_url="https://nlm.example.test",
    )
    with TestClient(_http_app(settings)) as client:
        protected = client.get("/.well-known/oauth-protected-resource")
        authorization = client.get("/.well-known/oauth-authorization-server")

    assert protected.status_code == HTTP_OK
    assert protected.json()["resource"] == "https://nlm.example.test"
    assert authorization.status_code == HTTP_OK
    assert authorization.json()["authorization_endpoint"] == ("https://nlm.example.test/auth/login")


def test_path_aware_oauth_protected_resource_metadata() -> None:
    settings = Settings(
        transport=TransportMode.HTTP,
        auth_mode=AuthMode.TOKEN,
        bearer_token=SecretStr("token"),
        base_url="https://nlm.example.test",
    )
    with TestClient(_http_app(settings)) as client:
        response = client.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == HTTP_OK
    payload = response.json()
    assert payload["resource"] == "https://nlm.example.test/mcp"
    assert payload["authorization_servers"] == ["https://nlm.example.test"]


def test_openapi_tool_action_invokes_mcp_tool() -> None:
    settings = Settings(transport=TransportMode.HTTP, auth_mode=AuthMode.NONE)
    with TestClient(_http_app(settings)) as client:
        response = client.post("/tools/admin.version", json={})

    assert response.status_code == HTTP_OK
    assert response.json()["name"] == "notebooklm-mcp-pro"
