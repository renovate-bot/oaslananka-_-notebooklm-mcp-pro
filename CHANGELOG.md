# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-05-12

### Added

- Research, artifact generation, artifact lifecycle, and language tool families.
- Persistent SQLite task tracking for artifact task ids and artifact metadata resources.
- Mind-map and artifact resources for generated NotebookLM content.
- Four typed workflow prompts for research summaries, study packs, meeting podcasts, and paper deep dives.
- Offline coverage for artifact generation, task polling, downloads, research import flow, language confirmation, prompts, and resources.

## [0.3.0] - 2026-05-11

### Added

- Notebook, source, and chat tool families with typed validation, annotations, and safe error handling.
- ChatGPT-compatible `search` and `fetch` tools for notebook/source record discovery.
- Core NotebookLM resources for notebook indexes, source metadata, and source full text.
- Offline fake-backend unit coverage and stdio smoke validation for the expanded tool catalog.

## [0.2.0] - 2026-05-11

### Added

- Async NotebookLM backend wrapper around `notebooklm-py`.
- Safe backend exception mapping for MCP-compatible error responses.
- Tenacity retry policy for rate-limit, timeout, server, and network failures.
- Offline unit coverage for auth source resolution, retry behavior, and wrapper delegation.

## [0.1.0] - 2026-05-11

### Added

- FastMCP server factory with stdio transport wiring.
- Settings model, structured logging setup, and admin health/version tools.
- Unit and integration smoke coverage for the core server skeleton.

## [0.0.1] - 2026-05-11

### Added

- Bootstrap scaffold for the NotebookLM MCP server project.
