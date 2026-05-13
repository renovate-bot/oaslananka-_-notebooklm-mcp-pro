# Tool Catalog

| Tool Name | Title | Read-only | Destructive | Description |
|---|---|---:|---:|---|
| admin.health | Server Health | yes | no | Return local server health and selected safe configuration fields. |
| admin.version | Server Version | yes | no | Return package, Python, and FastMCP version metadata. |
| artifact.cancel | Cancel Artifact Task | no | yes | Cancel a running artifact generation task after explicit confirmation. |
| artifact.delete | Delete Artifact | no | yes | Delete a generated artifact after explicit confirmation. |
| artifact.download | Download Artifact | yes | no | Download an artifact to a local path and return the written path. |
| artifact.list | List Artifacts | yes | no | List artifacts in a NotebookLM notebook. |
| artifact.revise_slide | Revise Slide | no | no | Revise one slide in a generated slide deck. |
| artifact.status | Artifact Status | yes | no | Poll a NotebookLM artifact task. |
| artifact.wait | Wait For Artifact | yes | no | Wait for an artifact task to complete. |
| chat.ask | Ask Notebook | no | no | Ask a one-shot question against a NotebookLM notebook. |
| chat.continue | Continue Conversation | no | no | Continue a NotebookLM conversation. |
| chat.conversation_start | Start Conversation | no | no | Start or identify the active NotebookLM conversation for a notebook. |
| chat.history | Chat History | yes | no | Get NotebookLM conversation history. |
| chat.list_notes | List Notebook Notes | yes | no | List saved NotebookLM notes. |
| chat.query | Query Notebook | no | no | Alias for `chat.ask` used by OpenAPI clients. |
| chat.save_note | Save Notebook Note | no | no | Alias for saving content as a NotebookLM note. |
| chat.save_to_notes | Save Chat Answer To Notes | no | no | Save a chat answer or drafted content as a NotebookLM note. |
| chat.stream_query | Stream Query Notebook | no | no | Run a NotebookLM query through the non-streaming backend and return one result. |
| fetch | Fetch NotebookLM Record | yes | no | Return one NotebookLM record as `{id, title, content, metadata}`. |
| generate.audio_overview | Generate Audio Overview | no | no | Generate an audio overview and return a task id. |
| generate.cinematic_video | Generate Cinematic Video | no | no | Generate a cinematic video and return a task id. |
| generate.data_table | Generate Data Table | no | no | Generate a data table and return a task id. |
| generate.flashcards | Generate Flashcards | no | no | Generate flashcards and return a task id. |
| generate.infographic | Generate Infographic | no | no | Generate an infographic and return a task id. |
| generate.mind_map | Generate Mind Map | no | no | Generate a mind map and return a task id. |
| generate.quiz | Generate Quiz | no | no | Generate a quiz and return a task id. |
| generate.report | Generate Report | no | no | Generate a report and return a task id. |
| generate.slide_deck | Generate Slide Deck | no | no | Generate a slide deck and return a task id. |
| generate.video_overview | Generate Video Overview | no | no | Generate a video overview and return a task id. |
| language.get | Get Language | yes | no | Get the current global NotebookLM output language. |
| language.list | List Languages | yes | no | List supported NotebookLM output languages. |
| language.set | Set Language | no | yes | Set the account-global NotebookLM output language after confirmation. |
| notebook.create | Create Notebook | no | no | Create a NotebookLM notebook with the supplied title. |
| notebook.delete | Delete Notebook | no | yes | Delete a NotebookLM notebook after explicit confirmation. |
| notebook.get | Get Notebook | yes | no | Get metadata for one NotebookLM notebook. |
| notebook.list | List Notebooks | yes | no | List all notebooks visible to the configured NotebookLM session. |
| notebook.rename | Rename Notebook | no | no | Rename one NotebookLM notebook. |
| notebook.share_invite | Invite Notebook Collaborator | no | yes | Invite an email address to view or edit a NotebookLM notebook. |
| notebook.share_public | Toggle Public Notebook Sharing | no | yes | Toggle public sharing for one NotebookLM notebook. |
| notebook.share_status | Notebook Sharing Status | yes | no | Return sharing settings for one NotebookLM notebook. |
| research.drive_start | Start Drive Research | no | no | Start a Google Drive research task for a notebook. |
| research.status | Research Status | yes | no | Poll the latest research task status for a notebook. |
| research.wait | Wait For Research | yes | no | Wait until the latest research task completes, optionally importing sources. |
| research.web_start | Start Web Research | no | no | Start a web research task for a notebook. |
| search | Search NotebookLM Records | yes | no | Return matching NotebookLM notebook and source record ids. |
| source.add_file | Add File Source | no | no | Upload a PDF, audio, video, image, text, markdown, or docx source. |
| source.add_gdrive | Add Google Drive Source | no | no | Add a Google Drive document as a source to a NotebookLM notebook. |
| source.add_text | Add Text Source | no | no | Paste raw text as a source in a NotebookLM notebook. |
| source.add_url | Add URL Source | no | no | Add a web URL as a source to a NotebookLM notebook. |
| source.add_youtube | Add YouTube Source | no | no | Add a YouTube URL as a source to a NotebookLM notebook. |
| source.get | Get Source | yes | no | Get metadata for one NotebookLM source. |
| source.get_fulltext | Get Source Full Text | yes | no | Retrieve indexed full text for one NotebookLM source. |
| source.list | List Sources | yes | no | List sources in a NotebookLM notebook. |
| source.refresh | Refresh Source | no | no | Re-index one NotebookLM source. |
| source.remove | Remove Source | no | yes | Remove a source from a NotebookLM notebook after explicit confirmation. |
| source.wait | Wait For Source | yes | no | Wait until one NotebookLM source leaves the indexing state. |

## Resources

| URI | Name | Description |
|---|---|---|
| notebooklm://notebooks | notebooks_resource | Return all notebooks as JSON. |

## Resource Templates

| Template | Name | Description |
|---|---|---|
| notebooklm://notebook/{id} | notebook_resource | Return notebook metadata and source index as JSON. |
| notebooklm://notebook/{id}/source/{src_id} | source_resource | Return source metadata as JSON. |
| notebooklm://notebook/{id}/source/{src_id}/fulltext | source_fulltext_resource | Return source full text as JSON. |
| notebooklm://notebook/{id}/mindmap | mindmap_resource | Return mind-map artifacts for a notebook as JSON. |
| notebooklm://artifact/{task_id} | artifact_resource | Return tracked artifact metadata as JSON. |

## Prompts

| Prompt | Title | Description |
|---|---|---|
| meeting-to-podcast | Meeting To Podcast | Ingest a transcript and generate an audio overview. |
| paper-deep-dive | Paper Deep Dive | Ingest a paper and generate video, slides, and report artifacts. |
| study-pack | Study Pack | Generate quiz, flashcards, and mind map artifacts. |
| summarize-research | Summarize Research | Build a notebook from URLs and generate a requested artifact. |
