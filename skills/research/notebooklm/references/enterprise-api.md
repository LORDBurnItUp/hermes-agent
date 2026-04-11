# NotebookLM Enterprise API

Official Google Cloud API for NotebookLM Enterprise. Requires a Google Cloud project with the NotebookLM Enterprise API enabled.

## Prerequisites

1. Google Cloud project with billing enabled
2. NotebookLM Enterprise API enabled
3. `gcloud` CLI installed and authenticated
4. Appropriate IAM roles assigned

## Setup

```bash
# Install gcloud CLI (if not installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable the API
gcloud services enable discoveryengine.googleapis.com

# Get project number (needed for API calls)
gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)'
```

## Authentication

```bash
# Get access token
TOKEN=$(gcloud auth print-access-token)

# Set common variables
PROJECT_NUMBER="YOUR_PROJECT_NUMBER"
LOCATION="global"
BASE="https://global-discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_NUMBER/locations/$LOCATION"
```

## API Endpoints

### Notebooks

#### Create a notebook

```bash
curl -X POST "$BASE/notebooks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "My Research Notebook"
  }'
```

Response includes the notebook resource with its ID.

#### Get a notebook

```bash
curl "$BASE/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

#### List notebooks

```bash
curl "$BASE/notebooks" \
  -H "Authorization: Bearer $TOKEN"
```

#### Delete a notebook

```bash
curl -X DELETE "$BASE/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### Sources

#### Batch create sources (URLs)

```bash
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/sources:batchCreate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {
        "source": {
          "uri_source": {
            "uri": "https://example.com/article-1"
          }
        }
      },
      {
        "source": {
          "uri_source": {
            "uri": "https://example.com/article-2"
          }
        }
      }
    ]
  }'
```

#### Upload a file

```bash
curl -X POST "https://global-discoveryengine.googleapis.com/upload/v1alpha/projects/$PROJECT_NUMBER/locations/$LOCATION/notebooks/NOTEBOOK_ID/sources:uploadFile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Goog-Upload-File-Name: document.pdf" \
  -H "X-Goog-Upload-Protocol: raw" \
  -H "Content-Type: application/pdf" \
  --data-binary @./document.pdf
```

#### Get a source

```bash
curl "$BASE/notebooks/NOTEBOOK_ID/sources/SOURCE_ID" \
  -H "Authorization: Bearer $TOKEN"
```

#### List sources

```bash
curl "$BASE/notebooks/NOTEBOOK_ID/sources" \
  -H "Authorization: Bearer $TOKEN"
```

#### Batch delete sources

```bash
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/sources:batchDelete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "names": [
      "projects/PROJECT_NUMBER/locations/global/notebooks/NOTEBOOK_ID/sources/SOURCE_ID_1",
      "projects/PROJECT_NUMBER/locations/global/notebooks/NOTEBOOK_ID/sources/SOURCE_ID_2"
    ]
  }'
```

### Audio Overviews

#### Create an audio overview

```bash
curl -X POST "$BASE/notebooks/NOTEBOOK_ID/audioOverviews" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sourceIds": [{"id": "SOURCE_ID"}],
    "episodeFocus": "Key findings and methodology",
    "languageCode": "en"
  }'
```

Returns a long-running operation. Poll the notebook to check completion status.

#### Get audio overview

```bash
curl "$BASE/notebooks/NOTEBOOK_ID/audioOverviews/default" \
  -H "Authorization: Bearer $TOKEN"
```

#### Check audio overview status

```bash
curl "$BASE/notebooks/NOTEBOOK_ID" \
  -H "Authorization: Bearer $TOKEN"
```

The notebook response includes audio overview state (PROCESSING, COMPLETED, FAILED).

#### Delete an audio overview

```bash
curl -X DELETE "$BASE/notebooks/NOTEBOOK_ID/audioOverviews/default" \
  -H "Authorization: Bearer $TOKEN"
```

### Sharing

#### Share a notebook

```bash
curl -X POST "$BASE/notebooks/NOTEBOOK_ID:share" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountAndRoles": [
      {"email": "user@example.com", "role": "EDITOR"}
    ]
  }'
```

### Standalone Podcast API

Generate podcast-style audio from sources without creating a notebook. See the official docs at `https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/podcast-api`.

## Source Types

| Type | Field | Notes |
|------|-------|-------|
| URL | `uri_source.uri` | Web pages, articles |
| File upload | `uploadFile` endpoint | PDF, TXT, DOCX |
| Google Drive | `uri_source.uri` | Drive file URLs |
| YouTube | `uri_source.uri` | Video URLs (transcript extracted) |

## Limits

| Resource | Free | Plus/Pro | Enterprise |
|----------|------|----------|------------|
| Sources per notebook | 50 | 300 | 300+ |
| Notebooks per user | 100 | 500 | Higher |
| Single document size | 200 MB / 500k words | Same | Same |
| Chat queries per day | 50 | 500 | 5,000+ |
| Audio overviews per notebook | 1 | 1 | 1 |

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid request (check JSON body) |
| 401 | Token expired — refresh with `gcloud auth print-access-token` |
| 403 | API not enabled or insufficient permissions |
| 404 | Notebook or source not found |
| 429 | Rate limit exceeded — back off and retry |
| 500 | Internal server error — retry after delay |

## Python Client (google-cloud)

```python
# The official Python client (if available) uses google-cloud-discoveryengine
# pip install google-cloud-discoveryengine

from google.cloud import discoveryengine_v1alpha as discoveryengine

client = discoveryengine.NotebookServiceClient()

# Create notebook
notebook = client.create_notebook(
    parent=f"projects/{PROJECT_NUMBER}/locations/global",
    notebook=discoveryengine.Notebook(display_name="My Notebook"),
)
print(f"Created: {notebook.name}")
```

Note: The Python client library may lag behind the REST API. Check the latest version at https://pypi.org/project/google-cloud-discoveryengine/
