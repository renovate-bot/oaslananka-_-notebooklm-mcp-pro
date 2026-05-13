# Notebook Tools

## notebook.list

Lists all notebooks visible to the configured NotebookLM session.

Parameters: none.

Returns:

```json
{"notebooks": [{"id": "nb-1", "title": "Research", "source_count": 5}]}
```

Example:

```text
List all my notebooks.
```

## notebook.create

Creates a notebook.

Parameters:

| Name | Type | Required |
|---|---|---|
| `title` | string | yes |

## notebook.get

Gets metadata for one notebook.

Parameters: `notebook_id`.

## notebook.rename

Renames one notebook.

Parameters: `notebook_id`, `title`.

## notebook.delete

Deletes a notebook after explicit confirmation.

Parameters: `notebook_id`, `confirm=true`.

## notebook.share_public

Enables or disables public sharing.

Parameters: `notebook_id`, `public`, `confirm`.

## notebook.share_invite

Invites a collaborator.

Parameters: `notebook_id`, `email`, `role`, `notify`, `welcome_message`, `confirm`.

## notebook.share_status

Returns sharing settings.

Parameters: `notebook_id`.
