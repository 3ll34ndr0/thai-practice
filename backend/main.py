from __future__ import annotations

import json
import random
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from scoring import score_attempt
from stt import transcribe_thai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
SENTENCES = json.loads((BASE_DIR / "sentences.json").read_text(encoding="utf-8"))

# A few seconds of speech is well under 1MB; this just blocks obviously
# oversized/abusive uploads before they're forwarded (and billed) to Orchardrun.
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.url.path == "/api/submit":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_BYTES:
            return JSONResponse({"detail": "Audio file too large"}, status_code=413)
    return await call_next(request)


def get_sentence(exercise_id: str | None = None) -> dict:
    if exercise_id is None:
        return random.choice(SENTENCES)
    for sentence in SENTENCES:
        if sentence["id"] == exercise_id:
            return sentence
    raise HTTPException(404, "Unknown exercise id")


@app.get("/api/exercise")
@limiter.limit("30/minute")
def api_exercise(request: Request):
    return get_sentence()


@app.post("/api/submit")
@limiter.limit("6/minute")
async def api_submit(request: Request, exercise_id: str = Form(...), audio: UploadFile = File(...)):
    if not (audio.content_type or "").startswith("audio/"):
        raise HTTPException(400, "Uploaded file must be audio")

    sentence = get_sentence(exercise_id)
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Audio file too large")

    transcript = await transcribe_thai(audio_bytes, audio.filename or "recording.webm")
    result = score_attempt(sentence["thai"], transcript)
    return {"target": sentence["thai"], **result}


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
