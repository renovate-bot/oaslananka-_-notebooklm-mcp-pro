# Artifact Generation Tools

All generation tools return a `task_id`, `status`, `notebook_id`, `artifact_type`, and backend `result`.

## generate.audio_overview

Generates an audio overview. Parameters include `audio_format`, `audio_length`, `language`, `source_ids`, and `instructions`.

## generate.video_overview

Generates a video overview. Parameters include `video_format`, `video_style`, `language`, `source_ids`, and `instructions`.

## generate.cinematic_video

Generates a documentary-style video.

## generate.slide_deck

Generates a slide deck. Download as PDF or PPTX through `artifact.download`.

## generate.infographic

Generates an infographic with `orientation` and `detail_level`.

## generate.quiz

Generates a quiz with `quantity` and `difficulty`.

## generate.flashcards

Generates flashcards with `quantity` and `difficulty`.

## generate.report

Generates a briefing document, study guide, blog post, or custom report.

## generate.data_table

Generates a tabular CSV-style artifact.

## generate.mind_map

Generates a JSON mind map.

## artifact.list

Lists backend artifacts and locally tracked tasks.

## artifact.status

Polls one artifact task.

## artifact.wait

Blocks until completion or timeout.

## artifact.download

Downloads an artifact into the configured artifacts directory. `output_path` must be relative; absolute paths and parent traversal are rejected.

## artifact.delete

Deletes a generated artifact when the installed NotebookLM backend supports deletion. Requires `confirm=true`.

## artifact.cancel

Cancels a running task when the installed NotebookLM backend supports cancellation. Requires `confirm=true`.

## artifact.revise_slide

Revises one slide in a slide deck.
