import json

from agents.base_agent import BaseAgent

BASE_DEPENDENCIES = {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
}

BASE_DEV_DEPENDENCIES = {
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.3.1",
    "tailwindcss": "^3.4.10",
    "postcss": "^8.4.41",
    "autoprefixer": "^10.4.20",
}

KNOWN_VERSIONS = {
    "react-router-dom": "^6.26.0",
    "recharts": "^2.12.7",
    "framer-motion": "^11.3.0",
    "lucide-react": "^0.408.0",
    "clsx": "^2.1.1",
}


class PackageAgent(BaseAgent):
    """
    In a fully local deployment this agent would shell out to `npm install`
    and `npm run build` inside a sandbox. A publicly hosted Streamlit app
    has no Node.js runtime available to it, so this agent instead
    deterministically resolves the dependency list from the Planner's
    output and emits a ready-to-use package.json plus the exact commands
    a developer runs locally to install and build. This tradeoff is
    called out explicitly in the README's known-limitations section.
    """

    name = "Package Manager Agent"

    def build_package_json(self, plan: dict) -> tuple[str, list]:
        deps = dict(BASE_DEPENDENCIES)
        skipped = []

        for dep in plan.get("dependencies", []):
            if dep in KNOWN_VERSIONS:
                deps[dep] = KNOWN_VERSIONS[dep]
            elif dep in BASE_DEV_DEPENDENCIES:
                # Planner sometimes names something (like "tailwindcss")
                # that's already pinned as a dev dependency in the
                # scaffold — nothing to add, just skip it quietly.
                continue
            else:
                # An LLM can invent a package name that isn't real, or
                # name a real package we've never vetted a version for.
                # Installing it at "latest" is exactly what broke a build
                # once already (a Tailwind/Vite plugin with an
                # incompatible peer dependency caused an ERESOLVE
                # failure) — so anything outside the whitelist is
                # dropped rather than guessed at.
                skipped.append(dep)

        manifest = {
            "name": plan.get("app_name", "generated-app").lower().replace(" ", "-"),
            "private": True,
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
            },
            "dependencies": dict(sorted(deps.items())),
            "devDependencies": dict(sorted(BASE_DEV_DEPENDENCIES.items())),
        }
        return json.dumps(manifest, indent=2), skipped

    @staticmethod
    def install_instructions() -> str:
        return "npm install\nnpm run dev      # local dev server\nnpm run build    # production build"
