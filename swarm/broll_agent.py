"""Generative B-roll agent.

Calls a generative-video API (Sora, Veo, or any provider that returns
an MP4 URL given a text prompt) and yields a URL ready to drop into the
Shotstack B-roll track. The interface is provider-agnostic; concrete
``SoraProvider`` and ``VeoProvider`` implementations encode plausible
REST shapes for OpenAI Sora and Google Veo.

Dry-run mode returns a deterministic placeholder URL so the pipeline
can run end-to-end without live API access — which is the expected
default until we have provisioned access.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Protocol

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 60
DEFAULT_POLL_TIMEOUT_S = 240
DEFAULT_POLL_INTERVAL_S = 4.0

# Stable placeholder so dry-runs are reproducible. The URL points at a
# Shotstack-hosted stock asset which is safe to embed in a render.
PLACEHOLDER_BROLL_URL = (
    "https://shotstack-assets.s3.amazonaws.com/footage/finance-charts-1.mp4"
)


class BRollGenerationError(RuntimeError):
    """Raised when the generative video API fails — caught by the supervisor."""


@dataclass
class BRollResult:
    url: str
    provider: str
    duration_seconds: Optional[float] = None
    job_id: Optional[str] = None


class BRollProvider(Protocol):
    name: str

    def submit(self, prompt: str, *, duration_seconds: float) -> str: ...
    def poll(self, job_id: str) -> "tuple[str, Optional[str]]": ...


# ---------------------------------------------------------------------------
# Sora provider (OpenAI Sora 2-style REST shape)
# ---------------------------------------------------------------------------


class SoraProvider:
    """Concrete provider for OpenAI Sora-style endpoints.

    The exact endpoint and JSON shape will be finalised when we get
    production API access; the structure below mirrors the public
    preview shape (POST /v1/videos → poll GET /v1/videos/{id}).
    """

    name = "sora"
    base_url = "https://api.openai.com/v1/videos"

    def __init__(self, api_key: Optional[str] = None, *, timeout: int = DEFAULT_TIMEOUT_S) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("SORA_API_KEY")
        self.timeout = timeout
        if not self.api_key:
            raise BRollGenerationError("SORA_API_KEY / OPENAI_API_KEY not set for Sora provider.")

    def _headers(self) -> dict:
        return {"authorization": f"Bearer {self.api_key}", "content-type": "application/json"}

    def submit(self, prompt: str, *, duration_seconds: float) -> str:
        body = {
            "model": "sora-2",
            "prompt": prompt,
            "seconds": int(max(min(duration_seconds, 60), 4)),
            "size": "1080x1920",  # 9:16 short
        }
        try:
            resp = requests.post(self.base_url, headers=self._headers(), json=body, timeout=self.timeout)
        except requests.RequestException as exc:
            raise BRollGenerationError(f"Sora submit network error: {exc}") from exc
        if resp.status_code not in (200, 201, 202):
            raise BRollGenerationError(
                f"Sora HTTP {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json() or {}
        job_id = data.get("id")
        if not job_id:
            raise BRollGenerationError(f"Sora response missing id: {data}")
        return job_id

    def poll(self, job_id: str) -> "tuple[str, Optional[str]]":
        url = f"{self.base_url}/{job_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise BRollGenerationError(f"Sora poll network error: {exc}") from exc
        if resp.status_code != 200:
            raise BRollGenerationError(f"Sora poll HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json() or {}
        status = (data.get("status") or "").lower()
        out_url = (data.get("output") or {}).get("url") or data.get("url")
        return status, out_url


# ---------------------------------------------------------------------------
# Veo provider (Google Veo 3.x-style REST shape via Vertex AI)
# ---------------------------------------------------------------------------


class VeoProvider:
    """Concrete provider for Google Veo via Vertex AI's predictLongRunning."""

    name = "veo"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model: str = "veo-3.1-generate-preview",
        timeout: int = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("VEO_API_KEY")
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.model = model
        self.timeout = timeout
        if not self.api_key or not self.project_id:
            raise BRollGenerationError(
                "Veo provider needs GOOGLE_API_KEY and GOOGLE_CLOUD_PROJECT."
            )

    def _endpoint(self, verb: str) -> str:
        return (
            f"https://{self.location}-aiplatform.googleapis.com/v1/projects/"
            f"{self.project_id}/locations/{self.location}/publishers/google/"
            f"models/{self.model}:{verb}"
        )

    def _headers(self) -> dict:
        return {"authorization": f"Bearer {self.api_key}", "content-type": "application/json"}

    def submit(self, prompt: str, *, duration_seconds: float) -> str:
        body = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "aspectRatio": "9:16",
                "durationSeconds": int(max(min(duration_seconds, 60), 4)),
                "sampleCount": 1,
            },
        }
        try:
            resp = requests.post(
                self._endpoint("predictLongRunning"),
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise BRollGenerationError(f"Veo submit network error: {exc}") from exc
        if resp.status_code not in (200, 201):
            raise BRollGenerationError(f"Veo HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json() or {}
        op = data.get("name")
        if not op:
            raise BRollGenerationError(f"Veo response missing operation name: {data}")
        return op

    def poll(self, job_id: str) -> "tuple[str, Optional[str]]":
        body = {"operationName": job_id}
        try:
            resp = requests.post(
                self._endpoint("fetchPredictOperation"),
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise BRollGenerationError(f"Veo poll network error: {exc}") from exc
        if resp.status_code != 200:
            raise BRollGenerationError(f"Veo poll HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json() or {}
        done = bool(data.get("done"))
        videos = (data.get("response") or {}).get("videos") or []
        url = videos[0].get("uri") if videos else None
        return ("succeeded" if done and url else ("succeeded" if done else "processing")), url


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


_PROVIDERS = {"sora": SoraProvider, "veo": VeoProvider}


def generate_broll(
    *,
    prompt: str,
    duration_seconds: float = 30.0,
    provider_name: Optional[str] = None,
    poll_timeout: int = DEFAULT_POLL_TIMEOUT_S,
    poll_interval: float = DEFAULT_POLL_INTERVAL_S,
    dry_run: bool = False,
) -> BRollResult:
    """Submit ``prompt`` to a generative video API and return the MP4 URL.

    In ``dry_run`` mode (or when no provider is configured), returns a
    stable placeholder URL.
    """
    if not prompt or not prompt.strip():
        raise BRollGenerationError("Empty visual_prompt — nothing to generate.")

    provider_name = (provider_name or os.environ.get("SWARM_BROLL_PROVIDER") or "").lower()

    if dry_run or not provider_name:
        # Deterministic placeholder URL keyed by prompt for traceability.
        digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8]
        logger.info(
            "B-roll dry-run (provider=%s prompt_hash=%s); returning placeholder.",
            provider_name or "stock",
            digest,
        )
        return BRollResult(
            url=PLACEHOLDER_BROLL_URL,
            provider=provider_name or "placeholder",
            duration_seconds=duration_seconds,
            job_id=f"dryrun-{digest}",
        )

    if provider_name not in _PROVIDERS:
        raise BRollGenerationError(
            f"Unknown B-roll provider {provider_name!r}; expected one of {list(_PROVIDERS)}"
        )

    provider = _PROVIDERS[provider_name]()
    job_id = provider.submit(prompt, duration_seconds=duration_seconds)
    logger.info("B-roll submit ok: provider=%s job_id=%s", provider.name, job_id)

    deadline = time.monotonic() + poll_timeout
    while time.monotonic() < deadline:
        status, url = provider.poll(job_id)
        status_l = status.lower()
        if status_l in {"succeeded", "completed", "ready"} and url:
            return BRollResult(url=url, provider=provider.name, duration_seconds=duration_seconds, job_id=job_id)
        if status_l in {"failed", "error", "cancelled"}:
            raise BRollGenerationError(f"{provider.name} job {job_id} reported status={status}")
        time.sleep(poll_interval)

    raise BRollGenerationError(
        f"{provider.name} job {job_id} did not finish within {poll_timeout}s."
    )
