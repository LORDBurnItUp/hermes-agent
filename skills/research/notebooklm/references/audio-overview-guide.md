# Audio Overview Guide

Audio overviews are podcast-style audio summaries generated from notebook sources. Two AI hosts discuss the content in a conversational format.

## Generation Options

### Formats

| Format | Description |
|--------|-------------|
| Deep dive | Full exploration of all sources (~10-20 min) |
| Brief | Quick summary (~3-5 min) |
| Critique | Critical analysis of the material |
| Debate | Two hosts take opposing perspectives |

### Lengths

- **Short** — ~3-5 minutes
- **Medium** — ~8-12 minutes (default)
- **Long** — ~15-25 minutes

### Custom Instructions

You can guide the audio generation with natural language instructions:

```bash
# Focus on specific topics
notebooklm generate audio "Focus only on the methodology section" --wait

# Set the tone
notebooklm generate audio "Explain this as if to a high school student" --wait

# Highlight specific aspects
notebooklm generate audio "Emphasize the practical applications and ignore the theoretical background" --wait
```

## Supported Languages

Audio overviews can be generated in 50+ languages. List them with:

```bash
notebooklm language list
```

Common languages: English, Spanish, French, German, Japanese, Korean, Chinese, Portuguese, Italian, Dutch, Russian, Arabic, Hindi.

## Tips for Better Audio

1. **Quality sources matter** — well-structured documents with clear headings produce better audio
2. **Source variety** — mixing different source types (articles, papers, videos) creates richer discussions
3. **Source count** — 3-5 focused sources typically produce better results than 20+ loosely related ones
4. **Custom instructions** — be specific about what to emphasize or skip
5. **Regeneration** — if the first result isn't great, regenerate with adjusted instructions

## Output Format

- **File format**: MP3
- **Sample rate**: 44.1 kHz
- **Channels**: Stereo (two AI hosts)
- **Typical size**: ~1 MB per minute

## Python Example

```python
import asyncio
from notebooklm import NotebookLMClient

async def generate_audio(notebook_id: str, output_path: str, instructions: str = ""):
    async with await NotebookLMClient.from_storage() as client:
        status = await client.artifacts.generate_audio(notebook_id, instructions=instructions)
        print(f"Generating audio (task: {status.task_id})...")
        await client.artifacts.wait_for_completion(notebook_id, status.task_id)
        await client.artifacts.download_audio(notebook_id, output_path)
        print(f"Audio saved to {output_path}")

asyncio.run(generate_audio("NOTEBOOK_ID", "output.mp3", "Keep it brief and technical"))
```

## Enterprise API

```bash
TOKEN=$(gcloud auth print-access-token)
PROJECT_NUMBER="YOUR_PROJECT_NUMBER"
BASE="https://global-discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_NUMBER/locations/global"

# Create audio overview
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/audioOverviews" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Check status (poll until state is COMPLETED)
curl "$BASE/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer $TOKEN"

# Delete audio overview
curl -X DELETE "$BASE/notebooks/NOTEBOOK_ID/audioOverviews/AUDIO_OVERVIEW_ID" \
  -H "Authorization: Bearer $TOKEN"
```
