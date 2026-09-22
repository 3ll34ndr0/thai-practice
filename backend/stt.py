import logging
import os
from pathlib import Path

import httpx
from fastapi import HTTPException

ORCHARDRUN_STT_URL = "https://api.orchardrun.com/v1/audio/transcriptions"

logger = logging.getLogger("stt")
DEBUG_AUDIO_PATH = Path("/tmp/last_recording.webm")

# Off by default: recordings are voice data and shouldn't be written to disk
# or logged in a public deployment. Set STT_DEBUG=1 locally to inspect them.
DEBUG_ENABLED = os.environ.get("STT_DEBUG") == "1"


async def transcribe_thai(audio_bytes: bytes, filename: str) -> str:
    api_key = os.environ.get("ORCHARDRUN_API_KEY")
    if not api_key:
        raise HTTPException(500, "Server is missing ORCHARDRUN_API_KEY")

    if DEBUG_ENABLED:
        DEBUG_AUDIO_PATH.write_bytes(audio_bytes)
        logger.warning("received audio: %d bytes -> saved to %s", len(audio_bytes), DEBUG_AUDIO_PATH)

    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": (filename, audio_bytes)}
    data = {"language": "th", "response_format": "verbose_json"}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(ORCHARDRUN_STT_URL, headers=headers, files=files, data=data)

    if resp.status_code != 200:
        # Log the real upstream error server-side, but don't leak it to the
        # client (could reveal account/billing details or internal shape).
        logger.error("Orchardrun STT error %d: %s", resp.status_code, resp.text)
        raise HTTPException(502, "Speech-to-text service is temporarily unavailable.")

    payload = resp.json()
    if DEBUG_ENABLED:
        logger.warning("orchardrun response: %s", payload)
    return payload.get("text", "")
