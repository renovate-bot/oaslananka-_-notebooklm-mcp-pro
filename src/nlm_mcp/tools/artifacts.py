"""NotebookLM artifact generation and lifecycle tools."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP

from nlm_mcp.backend.exceptions import BackendValidationError
from nlm_mcp.backend.tasks import TaskStore
from nlm_mcp.config import Settings
from nlm_mcp.tools.common import run_tool, stable_id, to_plain, tool_annotations
from nlm_mcp.tools.models import (
    ArtifactDownloadInput,
    ArtifactListInput,
    ArtifactStatusInput,
    ArtifactWaitInput,
    AudioOverviewInput,
    CinematicVideoInput,
    DataTableInput,
    GenerationTaskOutput,
    InfographicInput,
    MindMapInput,
    QuizLikeInput,
    ReportInput,
    ReviseSlideInput,
    SlideDeckInput,
    VideoOverviewInput,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from nlm_mcp.backend.client import NotebookLMBackend


def register_artifact_tools(
    server: FastMCP,
    backend: NotebookLMBackend,
    settings: Settings,
    *,
    task_store: TaskStore | None = None,
) -> None:
    """Register NotebookLM artifact tools."""
    store = task_store or TaskStore.from_settings(settings)

    @server.tool(
        name="generate.audio_overview",
        title="Generate Audio Overview",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_audio_overview(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        audio_format: str = "deep_dive",
        audio_length: str = "default",
    ) -> dict[str, Any]:
        """Generate an audio overview and return a task id."""
        payload = AudioOverviewInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "language": language,
                "instructions": instructions,
                "audio_format": audio_format,
                "audio_length": audio_length,
            }
        )
        return await run_tool(
            "generate.audio_overview",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "audio",
                backend.generate_audio_overview(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                    audio_format=payload.audio_format,
                    audio_length=payload.audio_length,
                ),
            ),
        )

    @server.tool(
        name="generate.video_overview",
        title="Generate Video Overview",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_video_overview(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        video_format: str = "explainer",
        video_style: str = "auto_select",
    ) -> dict[str, Any]:
        """Generate a video overview and return a task id."""
        payload = VideoOverviewInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "language": language,
                "instructions": instructions,
                "video_format": video_format,
                "video_style": video_style,
            }
        )
        return await run_tool(
            "generate.video_overview",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "video",
                backend.generate_video_overview(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                    video_format=payload.video_format,
                    video_style=payload.video_style,
                ),
            ),
        )

    @server.tool(
        name="generate.cinematic_video",
        title="Generate Cinematic Video",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_cinematic_video(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
    ) -> dict[str, Any]:
        """Generate a cinematic video and return a task id."""
        payload = CinematicVideoInput(
            notebook_id=notebook_id,
            source_ids=source_ids,
            language=language,
            instructions=instructions,
        )
        return await run_tool(
            "generate.cinematic_video",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "video",
                backend.generate_cinematic_video(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                ),
            ),
        )

    @server.tool(
        name="generate.slide_deck",
        title="Generate Slide Deck",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_slide_deck(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        slide_format: str = "detailed_deck",
        slide_length: str = "default",
    ) -> dict[str, Any]:
        """Generate a slide deck and return a task id."""
        payload = SlideDeckInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "language": language,
                "instructions": instructions,
                "slide_format": slide_format,
                "slide_length": slide_length,
            }
        )
        return await run_tool(
            "generate.slide_deck",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "slide_deck",
                backend.generate_slide_deck(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                    slide_format=payload.slide_format,
                    slide_length=payload.slide_length,
                ),
            ),
        )

    @server.tool(
        name="generate.infographic",
        title="Generate Infographic",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_infographic(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        orientation: str = "landscape",
        detail_level: str = "standard",
    ) -> dict[str, Any]:
        """Generate an infographic and return a task id."""
        payload = InfographicInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "language": language,
                "instructions": instructions,
                "orientation": orientation,
                "detail_level": detail_level,
            }
        )
        return await run_tool(
            "generate.infographic",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "infographic",
                backend.generate_infographic(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                    orientation=payload.orientation,
                    detail_level=payload.detail_level,
                ),
            ),
        )

    @server.tool(
        name="generate.quiz",
        title="Generate Quiz",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_quiz(
        notebook_id: str,
        source_ids: list[str] | None = None,
        instructions: str | None = None,
        quantity: str = "standard",
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """Generate a quiz and return a task id."""
        payload = QuizLikeInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "instructions": instructions,
                "quantity": quantity,
                "difficulty": difficulty,
            }
        )
        return await run_tool(
            "generate.quiz",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "quiz",
                backend.generate_quiz(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    instructions=payload.instructions,
                    quantity=payload.quantity,
                    difficulty=payload.difficulty,
                ),
            ),
        )

    @server.tool(
        name="generate.flashcards",
        title="Generate Flashcards",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_flashcards(
        notebook_id: str,
        source_ids: list[str] | None = None,
        instructions: str | None = None,
        quantity: str = "standard",
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """Generate flashcards and return a task id."""
        payload = QuizLikeInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "instructions": instructions,
                "quantity": quantity,
                "difficulty": difficulty,
            }
        )
        return await run_tool(
            "generate.flashcards",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "flashcards",
                backend.generate_flashcards(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    instructions=payload.instructions,
                    quantity=payload.quantity,
                    difficulty=payload.difficulty,
                ),
            ),
        )

    @server.tool(
        name="generate.report",
        title="Generate Report",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_report(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
        report_format: str = "briefing_doc",
        custom_prompt: str | None = None,
        extra_instructions: str | None = None,
    ) -> dict[str, Any]:
        """Generate a report and return a task id."""
        payload = ReportInput.model_validate(
            {
                "notebook_id": notebook_id,
                "source_ids": source_ids,
                "language": language,
                "instructions": instructions,
                "report_format": report_format,
                "custom_prompt": custom_prompt,
                "extra_instructions": extra_instructions,
            }
        )
        return await run_tool(
            "generate.report",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "report",
                backend.generate_report(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    report_format=payload.report_format,
                    custom_prompt=payload.custom_prompt,
                    extra_instructions=payload.extra_instructions or payload.instructions,
                ),
            ),
        )

    @server.tool(
        name="generate.data_table",
        title="Generate Data Table",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_data_table(
        notebook_id: str,
        source_ids: list[str] | None = None,
        language: str = "en",
        instructions: str | None = None,
    ) -> dict[str, Any]:
        """Generate a data table and return a task id."""
        payload = DataTableInput(
            notebook_id=notebook_id,
            source_ids=source_ids,
            language=language,
            instructions=instructions,
        )
        return await run_tool(
            "generate.data_table",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "data_table",
                backend.generate_data_table(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                    language=payload.language,
                    instructions=payload.instructions,
                ),
            ),
        )

    @server.tool(
        name="generate.mind_map",
        title="Generate Mind Map",
        annotations=tool_annotations(idempotent=False),
    )
    async def generate_mind_map(
        notebook_id: str,
        source_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a mind map and return a task id."""
        payload = MindMapInput(
            notebook_id=notebook_id,
            source_ids=source_ids,
        )
        return await run_tool(
            "generate.mind_map",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "mind_map",
                backend.generate_mind_map(
                    payload.notebook_id,
                    source_ids=payload.source_ids,
                ),
            ),
        )

    @server.tool(
        name="artifact.status",
        title="Artifact Status",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def artifact_status(notebook_id: str, task_id: str) -> dict[str, Any]:
        """Poll a NotebookLM artifact task."""
        payload = ArtifactStatusInput(notebook_id=notebook_id, task_id=task_id)
        return await run_tool(
            "artifact.status",
            payload,
            lambda: _status_task(store, backend, payload.notebook_id, payload.task_id),
        )

    @server.tool(
        name="artifact.wait",
        title="Wait For Artifact",
        annotations=tool_annotations(read_only=True, idempotent=False),
    )
    async def artifact_wait(
        notebook_id: str,
        task_id: str,
        poll_interval_sec: int = 15,
        timeout_sec: int = 600,
    ) -> dict[str, Any]:
        """Wait for an artifact task to complete."""
        payload = ArtifactWaitInput(
            notebook_id=notebook_id,
            task_id=task_id,
            poll_interval_sec=poll_interval_sec,
            timeout_sec=timeout_sec,
        )
        return await run_tool(
            "artifact.wait",
            payload,
            lambda: _wait_task(store, backend, payload),
        )

    @server.tool(
        name="artifact.list",
        title="List Artifacts",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def artifact_list(
        notebook_id: str,
        artifact_type: str | None = None,
    ) -> dict[str, Any]:
        """List artifacts in a NotebookLM notebook."""
        payload = ArtifactListInput.model_validate(
            {"notebook_id": notebook_id, "artifact_type": artifact_type}
        )
        return await run_tool(
            "artifact.list",
            payload,
            lambda: _list_artifacts(store, backend, payload),
        )

    @server.tool(
        name="artifact.download",
        title="Download Artifact",
        annotations=tool_annotations(read_only=True, idempotent=True),
    )
    async def artifact_download(
        notebook_id: str,
        artifact_type: str,
        output_path: str,
        artifact_id: str | None = None,
        output_format: str | None = None,
    ) -> dict[str, Any]:
        """Download an artifact to a local path and return the written path."""
        payload = ArtifactDownloadInput.model_validate(
            {
                "notebook_id": notebook_id,
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
                "output_path": output_path,
                "output_format": output_format,
            }
        )
        safe_payload = _safe_download_payload(settings, payload)
        return await run_tool(
            "artifact.download",
            safe_payload,
            lambda: _download_artifact(backend, safe_payload),
        )

    @server.tool(
        name="artifact.revise_slide",
        title="Revise Slide",
        annotations=tool_annotations(idempotent=False),
    )
    async def artifact_revise_slide(
        notebook_id: str,
        artifact_id: str,
        slide_index: int,
        prompt: str,
    ) -> dict[str, Any]:
        """Revise one slide in a generated slide deck."""
        payload = ReviseSlideInput(
            notebook_id=notebook_id,
            artifact_id=artifact_id,
            slide_index=slide_index,
            prompt=prompt,
        )
        return await run_tool(
            "artifact.revise_slide",
            payload,
            lambda: _submit_task(
                store,
                payload.notebook_id,
                "slide_revision",
                backend.revise_slide(
                    payload.notebook_id,
                    payload.artifact_id,
                    payload.slide_index,
                    payload.prompt,
                ),
            ),
        )


async def _submit_task(
    store: TaskStore,
    notebook_id: str,
    artifact_type: str,
    awaitable: Awaitable[Any],
) -> dict[str, Any]:
    result = to_plain(await awaitable)
    task_id = _task_id_from_result(result)
    default_status = "completed" if artifact_type == "mind_map" else "pending"
    status = _status_from_result(result, default=default_status)
    await store.upsert(
        task_id=task_id,
        notebook_id=notebook_id,
        kind=artifact_type,
        status=status,
        metadata={"result": result},
    )
    return GenerationTaskOutput(
        task_id=task_id,
        status=status,
        notebook_id=notebook_id,
        artifact_type=artifact_type,
        result=result,
    ).model_dump()


async def _status_task(
    store: TaskStore,
    backend: NotebookLMBackend,
    notebook_id: str,
    task_id: str,
) -> dict[str, Any]:
    status = to_plain(await backend.artifact_status(notebook_id, task_id))
    await store.upsert(
        task_id=task_id,
        notebook_id=notebook_id,
        kind=_kind_from_record(await store.get(task_id)),
        status=_status_from_result(status),
        metadata={"result": status},
    )
    return {"status": status}


async def _wait_task(
    store: TaskStore,
    backend: NotebookLMBackend,
    payload: ArtifactWaitInput,
) -> dict[str, Any]:
    status = to_plain(
        await backend.artifact_wait(
            payload.notebook_id,
            payload.task_id,
            initial_interval=float(payload.poll_interval_sec),
            max_interval=float(payload.poll_interval_sec),
            timeout=float(payload.timeout_sec),
        )
    )
    await store.upsert(
        task_id=payload.task_id,
        notebook_id=payload.notebook_id,
        kind=_kind_from_record(await store.get(payload.task_id)),
        status=_status_from_result(status),
        metadata={"result": status},
    )
    return {"status": status}


async def _list_artifacts(
    store: TaskStore,
    backend: NotebookLMBackend,
    payload: ArtifactListInput,
) -> dict[str, Any]:
    artifacts = to_plain(await backend.artifact_list(payload.notebook_id, payload.artifact_type))
    tasks = [record.__dict__ for record in await store.list_for_notebook(payload.notebook_id)]
    return {"artifacts": artifacts, "tracked_tasks": tasks}


def _normalize_output_format(output_format: str | None) -> str | None:
    if output_format == "md":
        return "markdown"
    return output_format


def _safe_download_payload(
    settings: Settings, payload: ArtifactDownloadInput
) -> ArtifactDownloadInput:
    requested = Path(payload.output_path)
    if requested.is_absolute():
        raise BackendValidationError(
            "artifact.download output_path must be relative.",
            error_code=-32602,
            data={"output_path": payload.output_path},
        )
    if ".." in requested.parts:
        raise BackendValidationError(
            "artifact.download output_path must not contain parent traversal.",
            error_code=-32602,
            data={"output_path": payload.output_path},
        )

    artifacts_dir = (settings.data_dir / "artifacts").resolve()
    resolved_path = (artifacts_dir / requested).resolve()
    if not resolved_path.is_relative_to(artifacts_dir):
        raise BackendValidationError(
            "artifact.download output_path must stay within the artifacts directory.",
            error_code=-32602,
            data={"output_path": payload.output_path},
        )

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return payload.model_copy(
        update={
            "output_path": str(resolved_path),
            "output_format": _normalize_output_format(payload.output_format),
        }
    )


async def _download_artifact(
    backend: NotebookLMBackend,
    payload: ArtifactDownloadInput,
) -> dict[str, Any]:
    output_path = await backend.artifact_download(
        payload.notebook_id,
        payload.artifact_type,
        payload.output_path,
        artifact_id=payload.artifact_id,
        output_format=payload.output_format,
    )
    return {
        "artifact_id": payload.artifact_id,
        "artifact_type": payload.artifact_type,
        "path": to_plain(output_path),
    }


def _task_id_from_result(result: Any) -> str:
    if isinstance(result, dict):
        for key in ("task_id", "artifact_id", "id", "note_id"):
            value = result.get(key)
            if value:
                return str(value)
    return stable_id(result, "task_id", "artifact_id", "note_id")


def _status_from_result(result: Any, *, default: str = "pending") -> str:
    if isinstance(result, dict):
        value = result.get("status")
        if value:
            return str(value)
    return default


def _kind_from_record(record: Any) -> str:
    return record.kind if record is not None else "unknown"
