# FrontForge AI

Turns a plain-English app description into a working React frontend
project, using a pipeline of agents rather than one big prompt. Built
from the FrontForge AI capstone brief, with two things added on top:

- **A style swapper.** Once a component is generated, its colors and
  shape can be changed with one click, editing the generated code
  directly, instead of asking an agent to rewrite it.
- **A working build and preview.** The backend runs `npm install` and
  `npm run build` itself and shows you the built app, not a rough
  stand-in for it.

## Why this isn't Streamlit

An earlier version used Streamlit. Two problems with that: it only
exposes one port once deployed, and there's no reliable way to get a
Node.js runtime running alongside it. Both matter here, since showing
what the app looks like means actually running npm and serving what it
builds.

This version is a small FastAPI backend with a plain HTML/JS frontend,
packaged in a Docker image that has Python and Node.js installed
together. `npm install` and `npm run build` run for real, and the built
app is served from the same server and port as the rest of the app.

## What it does

1. You describe the app you want.
2. The Clarification Agent asks a few short questions (framework,
   styling, theme, complexity). Answer them, or skip and it uses
   defaults.
3. A pipeline of agents plans the pages and components, decides the
   folder structure, generates each component (using a small local
   documentation set for context), applies a consistent theme, resolves
   npm dependencies, and reviews the result. Progress shows up as each
   agent finishes.
4. You can browse every generated file, download the project as a zip,
   and change any component's color theme or shape instantly.
5. "Install & build with npm" runs the build and shows the app in an
   iframe at `/preview/<session_id>/`. Style changes trigger a quick
   rebuild — the slow step, `npm install`, only runs once per session.

## Agent pipeline

| Agent | Job |
|---|---|
| Clarification | Asks a few targeted questions, falls back to defaults if skipped |
| Planner | Turns the answers into a plan of pages, components, and dependencies |
| UI Architect | Lays out the folder and file structure |
| Component | Generates each component's code, using retrieved documentation notes as context |
| Styling | Writes the global theme file and records which color preset each component uses |
| Package Manager | Resolves npm dependencies and writes package.json |
| Reviewer | Runs basic static checks and an LLM pass over the generated code |

## The style swapper

Components are styled with Tailwind utility classes, and a component's
color scheme comes down to a few prefixes (`bg-`, `text-`, `border-`,
`from-`, `to-`, `ring-`) combined with a color name and a shade number.
Each component remembers which preset it was generated with, and
switching presets swaps the color names for that component, keeping the
shade numbers (and the contrast/hover behavior they carry) unchanged.
Shape and elevation (rounded corners, shadows) swap the same way. Both
are plain text edits to code that already exists, so they're instant —
no model call — and a rebuild follows so the preview matches.

## Retrieval-augmented generation

A small local set of notes on React, Tailwind, React Router, Recharts,
Framer Motion, and common layout patterns is searched with TF-IDF
similarity before each component is generated, and the closest matches
go into the Component Agent's prompt.

A full crawl of official docs and template repositories, as described in
the original brief, was left out to keep the app light and fast to
start.

## Model

Agents run on **Ollama by default** — local, open-source inference with
no cloud dependency, matching the capstone brief's requirement (Section
1.2/2.2: zero calls to external APIs, on-device inference via Ollama or
llama.cpp). Any of the brief's recommended models work: Llama 3.2 (the
default), Qwen2.5, Gemma 2, or Phi-3.

**Groq remains available as an opt-in cloud fallback**, used only for
the separately deployed public link (a deployed server has no way to
reach an Ollama instance running on someone's own machine). Switching
between them is one environment variable — nothing in the code changes.

### Running with Ollama (default, matches the capstone brief)

1. Install Ollama: https://ollama.com/download
2. Pull a model: `ollama pull llama3.2`
3. Start it: `ollama serve` (often already running after install)
4. Run the app as usual — `LLM_PROVIDER` defaults to `ollama`, so no
   further setup is needed. The Settings tab shows whether Ollama is
   currently reachable.

To use a different model:
```bash
export OLLAMA_MODEL=qwen2.5:7b   # or gemma2:9b, phi3, etc.
```

CPU-only inference can be slow for larger models — `OLLAMA_TIMEOUT_SECONDS`
(default 180) controls how long a single agent call is allowed to take
before it's treated as failed rather than just slow.

### Running with Groq (for a publicly deployed instance)

```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=your-key-here
```

Get a free key at console.groq.com. This is what the deployed Render
instance uses, since Ollama isn't reachable from a public URL.

## Running locally

Requirements: Python 3.11+, Node.js 18+, npm. For the default Ollama
setup, also install Ollama (see above).

```bash
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY only if using LLM_PROVIDER=groq
uvicorn main:app --reload
```

Open http://localhost:8000. Get a free Groq API key at console.groq.com.
If you don't set `GROQ_API_KEY` in `.env`, you can also paste a key into
the Settings tab in the app (kept in memory for that session only).

## Deploying

This deploys as a Docker container, which is the simplest way to
guarantee Node.js is present alongside Python. Any host that runs a
Dockerfile works: Render, Railway, Fly.io, a plain VPS.

**Render (free tier):**
1. Push this repo to GitHub.
2. Create a new "Web Service" on render.com, pick the repo, and choose
   "Docker" as the environment — it picks up the `Dockerfile`
   automatically.
3. Add an environment variable `GROQ_API_KEY` with your key.
4. Deploy. Render gives you a public URL to submit.

**Railway / Fly.io:** both also build from the `Dockerfile` directly —
point them at the repo, set `GROQ_API_KEY`, and deploy.

To check the image builds locally first:
```bash
docker build -t frontforge-ai .
docker run -p 8000:8000 -e GROQ_API_KEY=your-key frontforge-ai
```

### Two things to know about a Render free-tier deploy

**Cold starts.** A free Render service spins down after about 15 minutes
of no traffic. The next visit after that wakes it back up, which takes
50+ seconds — the page can look blank or hang during that window. It
isn't broken, it's just waking up. Open the link yourself a few minutes
before a demo or before a judge is likely to open it, and it'll load
normally. Worth saying this outright in a submission note too, so it
doesn't get mistaken for a bug: "First load after a period of
inactivity can take 30-60 seconds — that's Render's free tier waking
up, not a broken deploy."

**Groq API key.** If `GROQ_API_KEY` is set under Render's Environment
tab, the app works for everyone with no extra step. If it isn't set (or
you're running this somewhere that key didn't carry over), the app will
say "No Groq API key configured" the first time someone tries to
generate something — the fix is the Settings tab in the app itself:
paste a Groq key there and click "Save key for this session." That key
only lives in memory for that one session, not written to disk or
shared with other visitors.

## Known limitations

- The build only works where the deployment target actually runs the
  `Dockerfile` (or otherwise has Node.js installed). A platform that
  only runs `pip install && python app.py` without Docker support won't
  have npm — the app detects this and says so instead of failing
  silently.
- Sessions live in server memory and on local disk for the life of the
  process — restarting the server clears them. That's fine for a
  single-instance hackathon deployment, not something to rely on beyond
  that.
- The style swapper works on Tailwind class names, so code that departs
  from the generated project's conventions may not swap cleanly.
- The documentation set is a small curated list, not a full index of
  official docs and template repositories.
- Generated components use hardcoded/mock data throughout, since there's
  no backend in scope.

## Project structure

```
main.py                    FastAPI app: all routes, session/build orchestration
pipeline.py                 Runs the 7-agent pipeline for one generation request
config.py                   Model names, pipeline order, defaults
agents/                      One module per agent
rag/                         Local documentation knowledge base and retriever
style_swapper/               Presets and the instant swap logic
utils/                       LLM client, npm runner, scaffold templates, session store, zip export
static/                      Frontend: index.html, app.js, styles.css
Dockerfile                   Python + Node.js image used for deployment
```
