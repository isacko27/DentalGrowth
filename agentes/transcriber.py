"""
Transcriber — Dental Growth
============================
Servicio API que recibe URLs de video y devuelve transcripciones.
Usa AssemblyAI con el modelo universal-3-pro en español.

Puerto: 8002
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import time
import hashlib
import json
import os
import uvicorn
from config import ASSEMBLYAI_API_KEY, TRANSCRIBER_PORT

app = FastAPI(title="Transcriber — Dental Growth", version="1.0")

# Cache local de transcripciones para no gastar créditos innecesariamente
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_transcripciones")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _get_cached(url: str) -> Optional[dict]:
    path = os.path.join(CACHE_DIR, f"{_cache_key(url)}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(url: str, data: dict):
    path = os.path.join(CACHE_DIR, f"{_cache_key(url)}.json")
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)

headers_aai = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}


class TranscribeRequest(BaseModel):
    url: str
    language: str = "es"


class TranscribeResponse(BaseModel):
    text: str
    duration_seconds: Optional[float] = None
    words_count: int


@app.get("/")
def root():
    return {"agent": "Transcriber", "status": "running"}


@app.post("/transcribir", response_model=TranscribeResponse)
def transcribir(req: TranscribeRequest):
    """
    Recibe una URL de video/audio y devuelve la transcripción en texto.
    Usa cache local para no re-transcribir videos ya procesados.
    """
    # Verificar cache primero
    cached = _get_cached(req.url)
    if cached:
        return TranscribeResponse(**cached)

    # Crear transcripción en AssemblyAI
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers_aai,
        json={
            "audio_url": req.url,
            "language_code": req.language,
            "speech_models": ["universal-3-pro"]
        }
    )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"AssemblyAI error: {response.text}")

    transcript_id = response.json()["id"]

    # Polling hasta completar
    while True:
        response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers_aai
        )
        response.raise_for_status()
        data = response.json()
        status = data["status"]

        if status == "completed":
            text = data.get("text", "")
            duration = data.get("audio_duration")
            words = len(text.split()) if text else 0
            result = {"text": text, "duration_seconds": duration, "words_count": words}
            _save_cache(req.url, result)
            return TranscribeResponse(**result)
        elif status == "error":
            raise HTTPException(
                status_code=502,
                detail=f"Error en transcripción: {data.get('error', 'unknown')}"
            )

        time.sleep(3)


@app.get("/health")
def health():
    return {"status": "ok", "api_key_set": bool(ASSEMBLYAI_API_KEY)}


# ============================================================
# IA — ENDPOINT /ask (lenguaje natural)
# ============================================================

from agent_brain import ask_agent

TRANSCRIBER_BRAIN_PROMPT = """Sos el Transcriber de Dental Growth. Tu única función es transcribir videos/audios.

Cuando te pidan transcribir algo, usá la herramienta transcribe con la URL del video.
Respondé en español de Costa Rica. Sé conciso."""

TRANSCRIBER_TOOLS = [{
    "name": "transcribe",
    "description": "Transcribe un video/audio desde una URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL del video/audio"},
            "language": {"type": "string", "description": "Código de idioma (default: es)", "default": "es"}
        },
        "required": ["url"]
    }
}]


def _transcriber_tool_executor(name, input_data):
    if name == "transcribe":
        import httpx
        r = httpx.post(f"http://localhost:{TRANSCRIBER_PORT}/transcribir",
                       json={"url": input_data["url"], "language": input_data.get("language", "es")},
                       timeout=120)
        return r.json()
    return {"error": f"Herramienta desconocida: {name}"}


class AskRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    try:
        response = ask_agent(req.question, TRANSCRIBER_BRAIN_PROMPT, TRANSCRIBER_TOOLS, _transcriber_tool_executor)
        return {"response": response}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


if __name__ == "__main__":
    print("🔤 Transcriber iniciando en puerto", TRANSCRIBER_PORT)
    uvicorn.run(app, host="0.0.0.0", port=TRANSCRIBER_PORT)
