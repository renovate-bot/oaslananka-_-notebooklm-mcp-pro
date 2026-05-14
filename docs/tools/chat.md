# Chat Tools

## chat_ask

Asks a one-shot question against a notebook.

Parameters: `notebook_id`, `question`, `source_ids`.

## chat_query

Alias for `chat_ask` exposed for OpenAPI clients.

## chat_stream_query

Runs a query through the same backend and returns the completed response. It is registered separately for clients that expect a stream-oriented name.

## chat_conversation_start

Starts or identifies a conversation.

Parameters: `notebook_id`, `name`, `initial_question`.

## chat_continue

Continues a conversation.

Parameters: `notebook_id`, `question`, `conversation_id`, `source_ids`.

## chat_history

Gets conversation history.

Parameters: `notebook_id`, `limit`, `conversation_id`.

## chat_save_to_notes

Saves content as a NotebookLM note.

Parameters: `notebook_id`, `title`, `content`.

## chat_save_note

Alias for `chat_save_to_notes`.

## chat_list_notes

Lists saved notes.

Parameters: `notebook_id`, `limit`.
