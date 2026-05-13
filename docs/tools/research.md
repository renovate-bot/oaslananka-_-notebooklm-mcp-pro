# Research Tools

## research.web_start

Starts web research with NotebookLM.

Parameters: `notebook_id`, `query`, `mode`.

## research.drive_start

Starts Drive research.

Parameters: `notebook_id`, `query`.

## research.status

Polls the latest research task status for a notebook.

Parameters: `notebook_id`.

## research.wait

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
