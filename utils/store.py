"""
Minimal in-memory session store.

Each generation lives under its own session id: a temp folder on disk
(for the actual project files, so npm can operate on them) plus a dict
here holding everything the frontend needs to render (plan, files,
component metadata, RAG hits, review text, build status).

This is intentionally simple — a single Python process's worth of memory
— which is a fair tradeoff for a hackathon submission running as one
deployed instance. It is not meant to survive a server restart or scale
across multiple worker processes.
"""

import shutil
import tempfile
import time
import uuid
from pathlib import Path

BASE_TMP = Path(tempfile.gettempdir()) / "frontforge_sessions"
BASE_TMP.mkdir(parents=True, exist_ok=True)

_sessions: dict[str, dict] = {}


def create_session() -> str:
    session_id = uuid.uuid4().hex[:12]
    workdir = BASE_TMP / session_id
    workdir.mkdir(parents=True, exist_ok=True)
    _sessions[session_id] = {
        "created_at": time.time(),
        "workdir": workdir,
        "api_key": None,
        "questions": [],
        "spec": {},
        "plan": {},
        "structure": {},
        "files": {},
        "component_meta": {},
        "rag_log": {},
        "static_issues": [],
        "review_text": "",
        "clarification_count": 0,
        "pipeline_log": [],
        "build_status": "idle",  # idle | installing | building | success | failed
        "build_log": "",
        "npm_installed": False,
        "build_version": 0,  # bumped on every successful build, for cache-busting the preview
        "generation_status": "idle",  # idle | running | success | failed
        "generation_log": [],
    }
    return session_id


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise KeyError(f"Unknown session: {session_id}")
    return _sessions[session_id]


def session_exists(session_id: str) -> bool:
    return session_id in _sessions


def delete_session(session_id: str):
    session = _sessions.pop(session_id, None)
    if session and session["workdir"].exists():
        shutil.rmtree(session["workdir"], ignore_errors=True)


def cleanup_old_sessions(max_age_seconds: int = 3600 * 6):
    now = time.time()
    stale = [sid for sid, s in _sessions.items() if now - s["created_at"] > max_age_seconds]
    for sid in stale:
        delete_session(sid)
