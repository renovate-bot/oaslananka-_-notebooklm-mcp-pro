from __future__ import annotations

import os

import pytest


@pytest.mark.e2e
def test_e2e_requires_explicit_notebooklm_auth() -> None:
    if os.getenv("NLM_MCP_RUN_E2E") != "1":
        pytest.skip("Set NLM_MCP_RUN_E2E=1 to run live NotebookLM tests.")

    auth_file = os.getenv("NLM_MCP_NOTEBOOKLM_AUTH_FILE")
    auth_json = os.getenv("NLM_MCP_NOTEBOOKLM_AUTH_JSON")
    if not auth_file and not auth_json:
        pytest.fail("Live NotebookLM auth is required when NLM_MCP_RUN_E2E=1.")

    assert auth_file or auth_json
