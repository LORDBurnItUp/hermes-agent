"""YouTube publishing agent.

Phase 3 of the Swarm OS: once Shotstack finishes rendering, this node
downloads the MP4 and uploads it to YouTube as a Short via the
YouTube Data API v3.

Auth uses an OAuth refresh-token grant (no interactive flow); see
docs/swarm-os-architecture.md §11 for the one-time setup steps.
Required env vars when ``dry_run=False``:

    YOUTUBE_CLIENT_ID
    YOUTUBE_CLIENT_SECRET
    YOUTUBE_REFRESH_TOKEN

The agent uploads as ``privacyStatus="private"`` by default — flip the
``privacy`` argument or set ``YOUTUBE_DEFAULT_PRIVACY`` to ``"unlisted"``
or ``"public"`` once a channel has been QA'd.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_PRIVACY = "private"
DEFAULT_CATEGORY_ID = "25"  # "News & Politics" — closest stable bucket for finance education
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_TIMEOUT_S = 30


class PublishError(RuntimeError):
    """Raised on download / upload failure — caught by the supervisor."""


@dataclass
class PublishResult:
    video_id: str
    url: str
    privacy: str


def publish_to_youtube(
    *,
    video_url: str,
    title: str,
    description: str,
    tags: List[str],
    privacy: Optional[str] = None,
    category_id: str = DEFAULT_CATEGORY_ID,
    made_for_kids: bool = False,
    timeout: int = DEFAULT_TIMEOUT_S,
    dry_run: bool = False,
) -> PublishResult:
    """Download ``video_url`` and upload it to YouTube."""
    if not video_url:
        raise PublishError("video_url is required.")
    if not title:
        raise PublishError("title is required.")

    privacy = (privacy or os.environ.get("YOUTUBE_DEFAULT_PRIVACY") or DEFAULT_PRIVACY).lower()
    if privacy not in {"private", "unlisted", "public"}:
        raise PublishError(f"Invalid privacy {privacy!r}.")

    if dry_run:
        stub_id = f"dryrun-yt-{abs(hash(title)) % 10 ** 10:010d}"
        logger.info(
            "YouTube dry-run; would upload title=%r privacy=%s (%d tags)",
            title,
            privacy,
            len(tags),
        )
        return PublishResult(
            video_id=stub_id,
            url=f"https://www.youtube.com/shorts/{stub_id}",
            privacy=privacy,
        )

    access_token = _exchange_refresh_token(timeout=timeout)
    with _download(video_url, timeout=timeout) as mp4_path:
        video_id = _resumable_upload(
            mp4_path=mp4_path,
            access_token=access_token,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
            category_id=category_id,
            made_for_kids=made_for_kids,
            timeout=timeout,
        )

    return PublishResult(
        video_id=video_id,
        url=f"https://www.youtube.com/shorts/{video_id}",
        privacy=privacy,
    )


# ---------------------------------------------------------------------------
# OAuth refresh-token flow
# ---------------------------------------------------------------------------


def _exchange_refresh_token(*, timeout: int) -> str:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not all((client_id, client_secret, refresh_token)):
        raise PublishError(
            "YouTube auth requires YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, "
            "YOUTUBE_REFRESH_TOKEN env vars. Pass dry_run=True for offline."
        )

    body = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        resp = requests.post(TOKEN_URL, data=body, timeout=timeout)
    except requests.RequestException as exc:
        raise PublishError(f"YouTube token exchange network error: {exc}") from exc
    if resp.status_code != 200:
        raise PublishError(f"YouTube token exchange HTTP {resp.status_code}: {resp.text[:200]}")
    token = (resp.json() or {}).get("access_token")
    if not token:
        raise PublishError("YouTube token exchange returned no access_token.")
    return token


# ---------------------------------------------------------------------------
# Download + resumable upload (raw requests — no googleapiclient dep)
# ---------------------------------------------------------------------------


class _download:
    """Context manager: streams a remote MP4 to a temp file, deletes on exit."""

    def __init__(self, url: str, *, timeout: int) -> None:
        self.url = url
        self.timeout = timeout
        self._path: Optional[Path] = None

    def __enter__(self) -> Path:
        fh = tempfile.NamedTemporaryFile(prefix="swarm-render-", suffix=".mp4", delete=False)
        self._path = Path(fh.name)
        try:
            with requests.get(self.url, stream=True, timeout=self.timeout) as r:
                if r.status_code != 200:
                    raise PublishError(
                        f"Could not download rendered video ({r.status_code} from {self.url})."
                    )
                for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MiB
                    if chunk:
                        fh.write(chunk)
        finally:
            fh.close()
        return self._path

    def __exit__(self, *exc) -> None:
        if self._path and self._path.exists():
            try:
                self._path.unlink()
            except OSError:
                pass


def _resumable_upload(
    *,
    mp4_path: Path,
    access_token: str,
    title: str,
    description: str,
    tags: List[str],
    privacy: str,
    category_id: str,
    made_for_kids: bool,
    timeout: int,
) -> str:
    """Two-step YouTube resumable upload: init session, then PUT bytes."""
    snippet_metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": [t for t in tags if t][:30],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": bool(made_for_kids),
        },
    }
    init_headers = {
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json; charset=UTF-8",
        "x-upload-content-type": "video/mp4",
        "x-upload-content-length": str(mp4_path.stat().st_size),
    }
    init_url = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )

    try:
        init = requests.post(init_url, headers=init_headers, json=snippet_metadata, timeout=timeout)
    except requests.RequestException as exc:
        raise PublishError(f"YouTube init network error: {exc}") from exc
    if init.status_code not in (200, 201):
        raise PublishError(f"YouTube upload init HTTP {init.status_code}: {init.text[:300]}")
    session_url = init.headers.get("location")
    if not session_url:
        raise PublishError("YouTube upload init returned no Location header.")

    with mp4_path.open("rb") as fh:
        upload_headers = {
            "authorization": f"Bearer {access_token}",
            "content-type": "video/mp4",
            "content-length": str(mp4_path.stat().st_size),
        }
        try:
            upload = requests.put(session_url, headers=upload_headers, data=fh, timeout=timeout * 10)
        except requests.RequestException as exc:
            raise PublishError(f"YouTube upload network error: {exc}") from exc

    if upload.status_code not in (200, 201):
        raise PublishError(f"YouTube upload HTTP {upload.status_code}: {upload.text[:300]}")
    body = upload.json() or {}
    video_id = body.get("id")
    if not video_id:
        raise PublishError(f"YouTube upload response missing id: {body}")
    return video_id
