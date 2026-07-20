"""
FastAPI backend for FrontForge AI.

Replaces the earlier Streamlit UI. The reasons: Streamlit only exposes
one port to the outside world and gives no reliable way to guarantee a
Node.js runtime, both of which get in the way of running and previewing
the *actual* built React app. A plain backend serving its own static
frontend, packaged in a Docker image that has Node.js installed
alongside Python, avoids both problems — npm runs for real, and the
built app is served from the same origin the rest of the app is on.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # picks up GROQ_API_KEY (and anything else) from a local .env file

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


def _api_key_for(session: dict) -> str | None:
    return session.get("api_key") or os.getenv("GROQ_API_KEY")


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
    else:
        detail = (
            "Groq API key configured" if ready else
            "No Groq API key configured — add one in Settings, or set "
            "GROQ_API_KEY as an environment variable."
        )
    return {"provider": LLM_PROVIDER, "ready": ready, "detail": detail}


def _session_or_404(session_id: str) -> dict:
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown or expired session")
    return get_session(session_id)


# ---------------------------------------------------------------------------
# Session + settings
# ---------------------------------------------------------------------------
@app.post("/api/session")
def new_session():
    cleanup_old_sessions()
    session_id = create_session()
    return {"session_id": session_id, "npm_available": npm_available(), "node_version": node_version()}


class SettingsIn(BaseModel):
    session_id: str
    api_key: str


@app.post("/api/settings")
def set_settings(body: SettingsIn):
    session = _session_or_404(body.session_id)
    session["api_key"] = body.api_key.strip() or None
    return {"ok": True}


@app.get("/api/llm-status/{session_id}")
def llm_status(session_id: str):
    session = _session_or_404(session_id)
    return _llm_status(session)


# ---------------------------------------------------------------------------
# Clarification
# ---------------------------------------------------------------------------
class ClarifyIn(BaseModel):
    session_id: str
    prompt: str


@app.post("/api/clarify")
def clarify(body: ClarifyIn):
    session = _session_or_404(body.session_id)
    llm = LLMClient(_api_key_for(session))
    agent = ClarificationAgent(llm)
    questions = agent.generate_questions(body.prompt) if llm.is_ready() else agent._default_questions()
    session["questions"] = questions
    return {"questions": questions}


# ---------------------------------------------------------------------------
# Generation (background task + polling)
# ---------------------------------------------------------------------------
class GenerateIn(BaseModel):
    session_id: str
    prompt: str
    answers: dict


@app.post("/api/generate")
def generate(body: GenerateIn, background_tasks: BackgroundTasks):
    session = _session_or_404(body.session_id)
    status = _llm_status(session)
    if not status["ready"]:
        raise HTTPException(status_code=400, detail=status["detail"])

    spec = ClarificationAgent.build_spec(body.prompt, body.answers)
    session["clarification_count"] = len(session.get("questions", []))
    session["generation_status"] = "running"
    session["generation_log"] = []
    session["build_status"] = "idle"
    session["npm_installed"] = False

    background_tasks.add_task(run_generation, session, spec, _api_key_for(session))
    return {"status": "started"}


@app.get("/api/generate-status/{session_id}")
def generate_status(session_id: str):
    session = _session_or_404(session_id)
    status = session["generation_status"]
    response = {"status": status, "log": session["generation_log"]}
    if status == "success":
        response["plan"] = session["plan"]
        response["static_issues"] = session["static_issues"]
        response["review_text"] = session["review_text"]
        response["clarification_count"] = session["clarification_count"]
        response["files"] = sorted(session["files"].keys())
        response["components"] = list(session["component_meta"].keys())
    return response


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
@app.get("/api/files/{session_id}")
def list_files(session_id: str):
    session = _session_or_404(session_id)
    return {"files": sorted(session["files"].keys())}


@app.get("/api/file/{session_id}")
def get_file(session_id: str, path: str):
    session = _session_or_404(session_id)
    if path not in session["files"]:
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "content": session["files"][path]}


# ---------------------------------------------------------------------------
# Style swapper
# ---------------------------------------------------------------------------
@app.get("/api/presets")
def presets():
    return {
        "color_presets": list(COLOR_PRESETS.keys()),
        "style_variants": list(STYLE_VARIANTS.keys()),
    }


class SwapIn(BaseModel):
    session_id: str
    component: str
    value: str  # preset name or variant name


@app.post("/api/swap-color")
def swap_color(body: SwapIn):
    session = _session_or_404(body.session_id)
    meta = session["component_meta"].get(body.component)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown component")

    path = f"src/components/{body.component}.jsx"
    session["files"][path] = swap_color_preset(session["files"][path], meta["preset"], body.value)
    meta["preset"] = body.value
    write_project_files(session["workdir"], {path: session["files"][path]})
    return {"code": session["files"][path], "preset": meta["preset"]}


@app.post("/api/swap-variant")
def swap_variant(body: SwapIn):
    session = _session_or_404(body.session_id)
    meta = session["component_meta"].get(body.component)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown component")

    path = f"src/components/{body.component}.jsx"
    session["files"][path] = swap_style_variant(session["files"][path], body.value)
    meta["variant"] = body.value
    write_project_files(session["workdir"], {path: session["files"][path]})
    return {"code": session["files"][path], "variant": meta["variant"]}


class ApplyAllIn(BaseModel):
    session_id: str
    preset: str


@app.post("/api/swap-color-all")
def swap_color_all(body: ApplyAllIn):
    session = _session_or_404(body.session_id)
    for name, meta in session["component_meta"].items():
        path = f"src/components/{name}.jsx"
        session["files"][path] = swap_color_preset(session["files"][path], meta["preset"], body.preset)
        meta["preset"] = body.preset
    write_project_files(session["workdir"], session["files"])
    return {"ok": True}


# ---------------------------------------------------------------------------
# Real npm install / build (background task + polling)
# ---------------------------------------------------------------------------
def _build_task(session: dict):
    workdir = session["workdir"]

    if not session["npm_installed"]:
        session["build_status"] = "installing"
        ok, log = npm_install(workdir)
        session["build_log"] = log
        if not ok:
            session["build_status"] = "failed"
            return
        session["npm_installed"] = True

    session["build_status"] = "building"
    ok, log = npm_build(workdir)
    session["build_log"] = log
    if not ok:
        session["build_status"] = "failed"
        return

    session["build_version"] += 1
    session["build_status"] = "success"


@app.post("/api/build/{session_id}")
def start_build(session_id: str, background_tasks: BackgroundTasks):
    session = _session_or_404(session_id)
    if not npm_available():
        raise HTTPException(status_code=400, detail="npm is not available on this host.")
    if not session["files"]:
        raise HTTPException(status_code=400, detail="Nothing generated yet.")

    session["build_status"] = "installing" if not session["npm_installed"] else "building"
    background_tasks.add_task(_build_task, session)
    return {"status": session["build_status"]}


@app.get("/api/build-status/{session_id}")
def build_status(session_id: str):
    session = _session_or_404(session_id)
    return {
        "status": session["build_status"],
        "log": session["build_log"],
        "build_version": session["build_version"],
        "npm_available": npm_available(),
        "node_version": node_version(),
    }


# ---------------------------------------------------------------------------
# Preview (serves the real built dist/ output for a session)
# ---------------------------------------------------------------------------
@app.get("/preview/{session_id}/")
@app.get("/preview/{session_id}/{file_path:path}")
def serve_preview(session_id: str, file_path: str = "index.html"):
    session = _session_or_404(session_id)
    dist_dir = dist_dir_for(session["workdir"])
    if not dist_dir.exists():
        raise HTTPException(status_code=404, detail="No build available yet for this session.")

    if file_path == "":
        file_path = "index.html"

    target = (dist_dir / file_path).resolve()
    if not target.is_relative_to(dist_dir.resolve()) or not target.exists():
        raise HTTPException(status_code=404, detail="File not found in build output.")
    return FileResponse(target)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
@app.get("/download/{session_id}/project.zip")
def download_project(session_id: str):
    session = _session_or_404(session_id)
    if not session["files"]:
        raise HTTPException(status_code=400, detail="Nothing generated yet.")
    app_name = session["plan"].get("app_name", "generated-app")
    zip_bytes = build_zip(session["files"], root_folder=app_name)
    tmp_path = session["workdir"] / "_project_export.zip"
    tmp_path.write_bytes(zip_bytes)
    return FileResponse(tmp_path, filename=f"{app_name}.zip", media_type="application/zip")


@app.get("/download/{session_id}/dist.zip")
def download_dist(session_id: str):
    session = _session_or_404(session_id)
    dist_dir = dist_dir_for(session["workdir"])
    if not dist_dir.exists():
        raise HTTPException(status_code=400, detail="No build available yet.")
    dist_files = collect_dist_files(dist_dir)
    zip_bytes = build_zip(dist_files, root_folder="dist")
    tmp_path = session["workdir"] / "_dist_export.zip"
    tmp_path.write_bytes(zip_bytes)
    return FileResponse(tmp_path, filename="dist.zip", media_type="application/zip")


# ---------------------------------------------------------------------------
# Frontend (static single page app)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
