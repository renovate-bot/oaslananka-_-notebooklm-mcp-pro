# Language Tools

## language_list

Lists supported output languages.

Returns:

```json
{"languages": [{"code": "en", "name": "English"}], "count": 80}
```

## language_get

Returns the current account-global NotebookLM output language.

## language_set

Sets the account-global output language. This affects the NotebookLM account, so it requires `confirm=true`.

Parameters: `language`, `confirm`.
