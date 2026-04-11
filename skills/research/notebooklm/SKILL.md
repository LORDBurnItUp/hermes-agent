---
name: notebooklm
description: >
  Full Google NotebookLM integration — create notebooks, manage sources (URLs,
  PDFs, text, YouTube, Google Drive), generate audio overviews and other
  artifacts, and query notebook content. Supports both the official NotebookLM
  Enterprise API (Google Cloud) and the notebooklm-py community SDK. Use when
  the user mentions NotebookLM, wants to create a podcast-style audio summary,
  or needs to organize and query research sources in a notebook.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [NotebookLM, Google, Research, Audio, Podcast, Sources, Notebooks, API]
    category: research
    related_skills: [google-workspace, arxiv, youtube-content]
---

# NotebookLM

Create and manage Google NotebookLM notebooks, add sources, generate audio overviews (podcast-style summaries), and query content programmatically.

## References

- `references/audio-overview-guide.md` — Audio overview generation options, formats, and languages
- `references/enterprise-api.md` — Official NotebookLM Enterprise API (Google Cloud) endpoints and setup

## Two Integration Paths

| Path | Best for | Auth | Setup time |
|------|----------|------|------------|
| **notebooklm-py** (community SDK) | Personal accounts, quick start, full feature set | Browser login | ~2 minutes |
| **Enterprise API** (Google Cloud) | Workspace orgs, production, compliance | Service account / OAuth2 | ~15 minutes |

Use `notebooklm-py` for most users. Use the Enterprise API only if the user has a Google Cloud project with NotebookLM Enterprise enabled.

---

## Path 1: notebooklm-py (Recommended)

### Setup

```bash
pip install notebooklm-py
pip install "notebooklm-py[browser]"   # needed for first-time login
playwright install chromium
```

### Authentication

First-time login opens a browser to authenticate with Google:

```bash
notebooklm login
# For Microsoft Edge SSO:
notebooklm login --browser msedge
```

Verify authentication:

```bash
notebooklm auth check --test
```

### CLI Usage

#### Notebook Management

```bash
# Create a notebook
notebooklm create "My Research Notebook"

# List all notebooks
notebooklm list

# Select a notebook to work with
notebooklm use NOTEBOOK_ID
```

#### Adding Sources

```bash
# Add a URL
notebooklm source add "https://example.com/article"

# Add a local PDF
notebooklm source add "./paper.pdf"

# Add via web research (auto-search and import)
notebooklm source add-research "transformer architecture improvements 2025"

# List sources in current notebook
notebooklm source list
```

#### Querying Content

```bash
# Ask a question about the notebook's sources
notebooklm ask "What are the key findings?"
notebooklm ask "Compare the methodologies used across the papers"
```

#### Generating Audio Overviews

```bash
# Generate a podcast-style audio overview
notebooklm generate audio --wait

# With custom instructions
notebooklm generate audio "Focus on the practical applications" --wait

# Download the audio
notebooklm download audio ./podcast.mp3
```

#### Other Artifacts

```bash
# Quiz
notebooklm generate quiz --difficulty hard
notebooklm download quiz --format json ./quiz.json

# Flashcards
notebooklm generate flashcards --quantity more
notebooklm download flashcards --format json ./cards.json

# Slide deck
notebooklm generate slide-deck
notebooklm download slide-deck ./slides.pdf

# Mind map
notebooklm generate mind-map
notebooklm download mind-map ./mindmap.json

# Report
notebooklm generate report
notebooklm download report ./report.md

# Data table
notebooklm generate data-table "Compare all models by accuracy and speed"
notebooklm download data-table ./data.csv

# Video overview
notebooklm generate video --style whiteboard --wait
notebooklm download video ./overview.mp4
```

#### Metadata and Sharing

```bash
# Export notebook metadata
notebooklm metadata --json

# Check sharing permissions
notebooklm share status

# List supported output languages
notebooklm language list
```

### Python API

```python
import asyncio
from notebooklm import NotebookLMClient

async def main():
    async with await NotebookLMClient.from_storage() as client:
        # Create a notebook
        nb = await client.notebooks.create("Research Project")

        # Add sources
        await client.sources.add_url(nb.id, "https://arxiv.org/abs/2402.03300", wait=True)
        await client.sources.add_file(nb.id, "./paper.pdf")

        # List sources
        sources = await client.sources.list(nb.id)
        for s in sources:
            print(f"  {s.title}")

        # Query the notebook
        result = await client.chat.ask(nb.id, "Summarize the key contributions")
        print(result.answer)

        # Generate and download audio overview
        status = await client.artifacts.generate_audio(nb.id, instructions="Keep it concise")
        await client.artifacts.wait_for_completion(nb.id, status.task_id)
        await client.artifacts.download_audio(nb.id, "podcast.mp3")
        print("Audio saved to podcast.mp3")

        # Generate quiz
        quiz_status = await client.artifacts.generate_quiz(nb.id)
        await client.artifacts.wait_for_completion(nb.id, quiz_status.task_id)
        await client.artifacts.download_quiz(nb.id, "quiz.json", "json")

asyncio.run(main())
```

### Key Python API Methods

| Module | Method | Description |
|--------|--------|-------------|
| `notebooks` | `create(name)` | Create a new notebook |
| `notebooks` | `list()` | List all notebooks |
| `sources` | `add_url(nb_id, url, wait=True)` | Add a URL source |
| `sources` | `add_file(nb_id, path)` | Add a local file (PDF, txt, etc.) |
| `sources` | `list(nb_id)` | List sources in a notebook |
| `sources` | `get_fulltext(source_id)` | Get indexed text of a source |
| `chat` | `ask(nb_id, question)` | Query notebook content |
| `artifacts` | `generate_audio(nb_id, instructions="")` | Start audio generation |
| `artifacts` | `generate_video(nb_id, style="")` | Start video generation |
| `artifacts` | `generate_quiz(nb_id)` | Generate a quiz |
| `artifacts` | `generate_flashcards(nb_id)` | Generate flashcards |
| `artifacts` | `generate_slide_deck(nb_id)` | Generate slides |
| `artifacts` | `generate_report(nb_id)` | Generate a report |
| `artifacts` | `generate_mind_map(nb_id)` | Generate a mind map |
| `artifacts` | `generate_data_table(nb_id)` | Generate a data table |
| `artifacts` | `wait_for_completion(nb_id, task_id)` | Wait for async generation |
| `artifacts` | `download_audio(nb_id, path)` | Download audio file |
| `artifacts` | `download_video(nb_id, path)` | Download video file |
| `artifacts` | `download_quiz(nb_id, path, fmt)` | Download quiz (json/md/html) |

---

## Path 2: Enterprise API (Google Cloud)

For organizations using Google Cloud with NotebookLM Enterprise enabled. See `references/enterprise-api.md` for full details.

### Quick Reference

Base URL: `https://global-discoveryengine.googleapis.com/v1alpha`

```bash
# Auth
TOKEN=$(gcloud auth print-access-token)
PROJECT_NUMBER="YOUR_PROJECT_NUMBER"
BASE="https://global-discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_NUMBER/locations/global"

# Create notebook
curl -X POST "$BASE/notebooks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "My Notebook"}'

# List notebooks
curl "$BASE/notebooks" -H "Authorization: Bearer $TOKEN"

# Add URL source
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/sources:batchCreate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requests": [{"source": {"uri_source": {"uri": "https://example.com"}}}]}'

# Generate audio overview
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/audioOverviews" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Get notebook (includes audio overview status)
curl "$BASE/notebooks/NOTEBOOK_ID" -H "Authorization: Bearer $TOKEN"

# Delete audio overview
curl -X DELETE "$BASE/notebooks/NOTEBOOK_ID/audioOverviews/AUDIO_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Common Workflows

### Research Paper Deep Dive

```bash
notebooklm create "Paper Review"
notebooklm source add "https://arxiv.org/abs/2402.03300"
notebooklm source add "./supplementary.pdf"
notebooklm ask "What is the main contribution of this paper?"
notebooklm ask "What are the limitations discussed?"
notebooklm generate audio "Explain the paper as if to a graduate student" --wait
notebooklm download audio ./paper-review.mp3
```

### Multi-Source Comparison

```bash
notebooklm create "Framework Comparison"
notebooklm source add "https://docs.example.com/framework-a"
notebooklm source add "https://docs.example.com/framework-b"
notebooklm source add "https://blog.example.com/comparison-review"
notebooklm ask "Compare the architectures of Framework A and B"
notebooklm generate data-table "Compare features, performance, and ecosystem"
notebooklm download data-table ./comparison.csv
```

### Content Repurposing

```bash
notebooklm create "Content Pack"
notebooklm source add "https://youtube.com/watch?v=VIDEO_ID"
notebooklm generate audio --wait
notebooklm generate slide-deck
notebooklm generate flashcards
notebooklm download audio ./podcast.mp3
notebooklm download slide-deck ./slides.pdf
notebooklm download flashcards --format json ./cards.json
```

## Rules

1. **Always verify authentication first** — run `notebooklm auth check --test` before attempting operations.
2. **Wait for generation to complete** — use `--wait` flag with `generate` commands or call `wait_for_completion()` in Python.
3. **Confirm before bulk operations** — ask the user before adding many sources or generating multiple artifacts.
4. **Source limits** — NotebookLM supports up to 50 sources per notebook and 500 pages per source.
5. **Audio generation takes time** — typically 2-5 minutes depending on source length.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `notebooklm: command not found` | `pip install notebooklm-py` |
| Auth fails | `notebooklm login` (needs `[browser]` extra + Playwright) |
| `playwright` error | `pip install "notebooklm-py[browser]" && playwright install chromium` |
| Source add hangs | Check network; try without `wait=True` and poll manually |
| Audio not generating | Ensure notebook has at least one source with indexed content |
| Enterprise API 403 | Verify project has NotebookLM Enterprise API enabled |
| Enterprise API 401 | Refresh token: `gcloud auth print-access-token` |

## Notes

- `notebooklm-py` uses undocumented Google APIs and may break with upstream changes
- The Enterprise API is in v1alpha and subject to change
- Audio overviews require at least one source to be fully indexed before generation
- Python 3.10+ required for `notebooklm-py`
