"""
Runs the agent pipeline for one generation request. Lives in its own
module so main.py stays focused on HTTP routing.

Designed to run inside a background task/thread: it mutates the session
dict's `generation_log` list as it goes, so the frontend can poll
/api/generate-status and show progress agent-by-agent instead of staring
at a spinner for 30+ seconds.
"""

import re

from agents.architect_agent import ArchitectAgent
from agents.component_agent import ComponentAgent
from agents.package_agent import KNOWN_VERSIONS, PackageAgent
from agents.planner_agent import PlannerAgent
from agents.reviewer_agent import ReviewerAgent
from agents.styling_agent import StylingAgent
from config import AGENT_LABELS
from style_swapper.presets import COLOR_PRESETS
from utils.llm_client import LLMClient, LLMError
from utils.npm_runner import write_project_files
from utils.scaffold import (
    app_jsx,
    index_html,
    main_jsx,
    postcss_config,
    project_readme,
    tailwind_config,
    vite_config,
)

IMPORT_PATTERN = re.compile(r"""from\s+['"]([^'"]+)['"]""")


def run_generation(session: dict, spec: dict, api_key: str | None):
    log = session["generation_log"]
    session["generation_status"] = "running"

    def emit(msg: str):
        log.append(msg)

    try:
        llm = LLMClient(api_key, on_retry=emit)

        planner_agent = PlannerAgent(llm)
        architect_agent = ArchitectAgent(llm)
        component_agent = ComponentAgent(llm)
        styling_agent = StylingAgent(llm)
        package_agent = PackageAgent(llm)
        reviewer_agent = ReviewerAgent(llm)

        files = {}
        component_meta = {}
        rag_log = {}

        emit(f"{AGENT_LABELS['clarification']}: specification confirmed.")

        emit(f"{AGENT_LABELS['planner']}: planning pages and components...")
        plan = planner_agent.generate_plan(spec)
        emit(f"{AGENT_LABELS['planner']}: {len(plan.get('pages', []))} page(s), "
             f"{len(plan.get('components', []))} component(s) planned.")

        emit(f"{AGENT_LABELS['architect']}: designing folder structure...")
        structure = architect_agent.generate_structure(plan)
        emit(f"{AGENT_LABELS['architect']}: laid out {len(structure['layout'])} files.")

        theme_colors = COLOR_PRESETS.get(spec["theme"], COLOR_PRESETS["Ocean Blue"])
        components_list = plan.get("components", [])
        use_router = len(plan.get("pages", [])) > 1
        if use_router and "react-router-dom" not in plan.get("dependencies", []):
            plan.setdefault("dependencies", []).append("react-router-dom")
        available_dependencies = [d for d in plan.get("dependencies", []) if d in KNOWN_VERSIONS]

        for comp in components_list:
            code, hits = component_agent.generate_component(comp, theme_colors, available_dependencies)
            path = f"src/components/{comp['name']}.jsx"
            files[path] = code
            component_meta[comp["name"]] = styling_agent.tag_component(comp["name"], spec["theme"])
            rag_log[comp["name"]] = hits
            emit(f"{AGENT_LABELS['component']}: generated {comp['name']} "
                 f"({len(hits)} doc snippet(s) retrieved).")

        for page in plan.get("pages", []):
            slug = page["name"].replace(" ", "")
            comps_on_page = [c["name"] for c in components_list if page["name"] in c.get("used_on_pages", [])]
            imports = "\n".join(f"import {c} from '../components/{c}.jsx'" for c in comps_on_page)
            body = "\n      ".join(f"<{c} />" for c in comps_on_page) or "<p>Nothing here yet.</p>"
            files[f"src/pages/{slug}.jsx"] = (
                f"import React from 'react'\n{imports}\n\n"
                f"export default function {slug}() {{\n  return (\n    <div>\n      {body}\n    </div>\n  )\n}}\n"
            )
        emit(f"{AGENT_LABELS['component']}: composed {len(plan.get('pages', []))} page file(s).")

        emit(f"{AGENT_LABELS['styling']}: writing global theme...")
        files["src/index.css"] = styling_agent.build_global_css(spec["theme"])
        used_libs = set()
        for path, code in files.items():
            if path.endswith((".jsx", ".tsx")):
                for match in IMPORT_PATTERN.finditer(code):
                    used_libs.add(match.group(1))
        missing_deps = sorted(
            lib for lib in used_libs
            if lib in KNOWN_VERSIONS and lib not in plan.get("dependencies", [])
        )
        if missing_deps:
            plan.setdefault("dependencies", []).extend(missing_deps)
            emit(
                f"{AGENT_LABELS['package']}: detected {len(missing_deps)} import(s) the plan "
                f"missed ({', '.join(missing_deps)}) and added them so the build doesn't break."
            )

        files["src/main.jsx"] = main_jsx()
        files["src/App.jsx"] = app_jsx(plan.get("pages", []), use_router)
        files["index.html"] = index_html(plan.get("app_name", "GeneratedApp"))
        files["vite.config.js"] = vite_config()
        files["tailwind.config.js"] = tailwind_config()
        files["postcss.config.js"] = postcss_config()
        files["README.md"] = project_readme(plan.get("app_name", "GeneratedApp"))

        emit(f"{AGENT_LABELS['package']}: resolving dependencies...")
        package_json, skipped_deps = package_agent.build_package_json(plan)
        files["package.json"] = package_json
        if skipped_deps:
            emit(
                f"{AGENT_LABELS['package']}: skipped {len(skipped_deps)} unrecognized "
                f"dependency name(s) ({', '.join(skipped_deps)}) rather than installing "
                f"them unpinned — safer than risking a broken build."
            )
        emit(f"{AGENT_LABELS['package']}: package.json written.")

        emit(f"{AGENT_LABELS['reviewer']}: reviewing generated code...")
        static_issues = reviewer_agent.static_checks(files)
        review_text = reviewer_agent.review(files, static_issues)
        emit(f"{AGENT_LABELS['reviewer']}: {len(static_issues)} static issue(s) found.")

        session["plan"] = plan
        session["structure"] = structure
        session["files"] = files
        session["component_meta"] = component_meta
        session["rag_log"] = rag_log
        session["static_issues"] = static_issues
        session["review_text"] = review_text
        session["spec"] = spec

        write_project_files(session["workdir"], files)

        emit("Done.")
        session["generation_status"] = "success"

    except LLMError as exc:
        emit(f"Error: {exc}")
        session["generation_status"] = "failed"
    except Exception as exc:  # noqa: BLE001
        emit(f"Unexpected error: {exc}")
        session["generation_status"] = "failed"
