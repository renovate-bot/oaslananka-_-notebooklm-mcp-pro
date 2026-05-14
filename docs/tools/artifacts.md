# Artifact Generation Tools

All generation tools return a `task_id`, `status`, `notebook_id`, `artifact_type`, and backend `result`.

## generate_audio_overview

Generates an audio overview. Parameters include `audio_format`, `audio_length`, `language`, `source_ids`, and `instructions`.

## generate_video_overview

Generates a video overview. Parameters include `video_format`, `video_style`, `language`, `source_ids`, and `instructions`.

## generate_cinematic_video

Generates a documentary-style video.

## generate_slide_deck

Generates a slide deck. Download as PDF or PPTX through `artifact_download`.

## generate_infographic

Generates an infographic with `orientation` and `detail_level`.

## generate_quiz

Generates a quiz with `quantity` and `difficulty`.

## generate_flashcards

Generates flashcards with `quantity` and `difficulty`.

## generate_report

Generates a briefing document, study guide, blog post, or custom report.

## generate_data_table

Generates a tabular CSV-style artifact.

## generate_mind_map

Generates a JSON mind map.

## artifact_list

Lists backend artifacts and locally tracked tasks.

## artifact_status

Polls one artifact task.

## artifact_wait

Blocks until completion or timeout.

## artifact_download

Downloads an artifact into the configured artifacts directory. `output_path` must be relative; absolute paths and parent traversal are rejected.

## artifact_delete

Deletes a generated artifact when the installed NotebookLM backend supports deletion. Requires `confirm=true`.

## artifact_cancel

Cancels a running task when the installed NotebookLM backend supports cancellation. Requires `confirm=true`.

## artifact_revise_slide

Revises one slide in a slide deck.
