# Source Tools

## source_add_url

Adds a web URL source. Parameters: `notebook_id`, `url`, `wait`.

## source_add_youtube

Adds a YouTube URL source. Parameters: `notebook_id`, `url`, `wait`.

## source_add_file

Uploads a local PDF, audio, video, image, text, markdown, or docx file. Parameters: `notebook_id`, `file_path`, `mime_type`, `wait`.

## source_add_gdrive

Adds a Google Drive document by file ID. Parameters: `notebook_id`, `file_id`, `title`, `mime_type`, `wait`.

## source_add_text

Adds pasted raw text. Parameters: `notebook_id`, `title`, `content`, `wait`.

## source_list

Lists sources in a notebook. Parameters: `notebook_id`.

## source_get

Gets one source metadata record. Parameters: `notebook_id`, `source_id`.

## source_get_fulltext

Retrieves indexed full text. Parameters: `notebook_id`, `source_id`.

## source_refresh

Requests re-indexing for a source. Parameters: `notebook_id`, `source_id`.

## source_wait

Waits until a source leaves a pending, processing, indexing, or refreshing state. Parameters: `notebook_id`, `source_id`, `poll_interval_sec`, `timeout_sec`.

## source_remove

Removes a source after explicit confirmation. Parameters: `notebook_id`, `source_id`, `confirm=true`.
