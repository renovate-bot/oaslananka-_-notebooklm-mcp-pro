# Language Tools

## language.list

Lists supported output languages.

Returns:

```json
{"languages": [{"code": "en", "name": "English"}], "count": 80}
```

## language.get

Returns the current account-global NotebookLM output language.

## language.set

Sets the account-global output language. This affects the NotebookLM account, so it requires `confirm=true`.

Parameters: `language`, `confirm`.
