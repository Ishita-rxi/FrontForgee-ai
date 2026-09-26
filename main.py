import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.clarification_agent import ClarificationAgent
from config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
from pipeline import run_generation
from style_swapper.presets import COLOR_PRESETS, STYLE_VARIANTS
from style_swapper.swapper import swap_color_preset, swap_style_variant
from utils.llm_client import LLMClient
from utils.npm_runner import (
    collect_dist_files,
    dist_dir_for,
    node_version,
    npm_available,
    npm_build,
    npm_install,
    write_project_files,
)
from utils.store import cleanup_old_sessions, create_session, get_session, session_exists
from utils.zip_export import build_zip

app = FastAPI(title="FrontForge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


_PROVIDER_ENV_KEYS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def _api_key_for(session: dict) -> str | None:
    env_key = _PROVIDER_ENV_KEYS.get(LLM_PROVIDER)
    return session.get("api_key") or (os.getenv(env_key) if env_key else None)


def _llm_status(session: dict) -> dict:
    """Used by both the readiness check before generating and the Settings
    tab, so the person always sees the same picture of what's configured."""
    llm = LLMClient(_api_key_for(session))
    ready = llm.is_ready()
    if LLM_PROVIDER == "ollama":
        detail = (
            f"Ollama reachable at {OLLAMA_BASE_URL} (model: {OLLAMA_MODEL})"
            if ready else
            f"Can't reach Ollama at {OLLAMA_BASE_URL}. Run `ollama serve` and "
            f"`ollama pull {OLLAMA_MODEL}`, then try again."
        )
    elif LLM_PROVIDER == "gemini":
        detail = (
            "Gemini API key configured" if ready else
            "No Gemini API key configured — add one in Settings, or set "
            "GEMINI_API_KEY as an environment variable."
        )
    else:
        detail = (
            "Groq API key configured" if ready else
            "No Groq API key configured — add one in Settings, or set "
            "GROQ_API_KEY as an environment variable."
        )
        if ready and os.getenv("GEMINI_API_KEY"):
            detail += " (Gemini fallback enabled if Groq's models fail.)"
    return {"provider": LLM_PROVIDER, "ready": ready, "detail": detail}


def _session_or_404(session_id: str) -> dict:
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown or expired session")
    return get_session(session_id)

