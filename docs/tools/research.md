# Research Tools

## research_web_start

Starts web research with NotebookLM.

Parameters: `notebook_id`, `query`, `mode`.

## research_drive_start

Starts Drive research.

Parameters: `notebook_id`, `query`.

## research_status

Polls the latest research task status for a notebook.

Parameters: `notebook_id`.

## research_wait

Waits for a research task to finish and can import discovered sources.

Parameters: `notebook_id`, `task_id`, `poll_interval_sec`, `timeout_sec`, `auto_import`, `max_sources`.

Example:

```json
{
  "notebook_id": "nb-1",
  "task_id": "research-1",
  "auto_import": true,
  "max_sources": 10
}
```
