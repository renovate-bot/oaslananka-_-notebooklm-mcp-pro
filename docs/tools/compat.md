# Compatibility Tools

## search

Returns matching notebook and source record IDs:

```json
{"ids": ["notebook:nb-1", "source:nb-1:src-1"]}
```

Parameters:

| Name | Type | Default |
|---|---|---|
| `query` | string | empty |
| `limit` | integer | `20` |

## fetch

Returns a full record by ID:

```json
{
  "id": "source:nb-1:src-1",
  "title": "Source title",
  "content": "Indexed source text",
  "metadata": {
    "kind": "source",
    "notebook_id": "nb-1",
    "source_id": "src-1"
  }
}
```

Supported ID shapes:

- `notebook:{notebook_id}`
- `source:{notebook_id}:{source_id}`

These tools are designed for ChatGPT Deep Research and company-knowledge style workflows that expect `search` and `fetch`.
