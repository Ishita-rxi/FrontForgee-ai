"""
Boilerplate that is identical for every generated app and therefore does
not need an LLM call — generating it deterministically is faster, cheaper,
and more reliable than asking a model to reproduce a Vite config from
memory.
"""


def index_html(app_name: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{app_name}</title>
    <script>
      // Plain (non-module) script, so this runs and registers its
      // listeners before any module code — including main.jsx and
      // everything it imports — has a chance to execute. ES modules
      // evaluate their imports before their own top-level code runs,
      // so a crash while a component is being *imported* (not just
      // while it's rendering) would otherwise happen before any
      // error handling defined inside main.jsx itself ever runs.
      function showFallbackError(title, detail) {{
        var root = document.getElementById('root');
        if (root && !root.hasChildNodes()) {{
          root.innerHTML =
            '<div style="padding:24px;font-family:monospace;color:#991b1b;background:#fef2f2;">' +
            '<h2 style="margin-top:0;">' + title + '</h2>' +
            '<p>' + detail + '</p>' +
            '<p style="color:#7f1d1d;">Open the browser console for the full stack trace.</p>' +
            '</div>';
        }}
      }}
      window.addEventListener('error', function(event) {{
        showFallbackError('Failed to load the app', event.message || 'Unknown error');
      }});
      window.addEventListener('unhandledrejection', function(event) {{
        var reason = event.reason && event.reason.message ? event.reason.message : String(event.reason);
        showFallbackError('Failed to load the app', reason);
      }});
    </script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""


def main_jsx() -> str:
    return """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Without this, a runtime error in any generated component leaves the
// page blank with no clue why — the crash only shows up in the browser
// console. This boundary catches render-time errors and shows them on
// screen instead, and the window listener below catches errors that
// happen before React even mounts.
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    console.error('Render error:', error, info)
  }
  render() {
    if (this.state.error) {
      const message = this.state.error && this.state.error.message
        ? this.state.error.message
        : String(this.state.error)
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: '#991b1b', background: '#fef2f2' }}>
          <h2 style={{ marginTop: 0 }}>This page crashed while rendering</h2>
          <p>{message}</p>
          <p style={{ color: '#7f1d1d' }}>Open the browser console for the full stack trace.</p>
        </div>
      )
    }
    return this.props.children
  }
}

window.addEventListener('error', (event) => {
  const root = document.getElementById('root')
  if (root && !root.hasChildNodes()) {
    root.innerHTML =
      '<div style="padding:24px;font-family:monospace;color:#991b1b;background:#fef2f2;">' +
      '<h2>Failed to load the app</h2><p>' + (event.message || 'Unknown error') + '</p>' +
      '<p>Open the browser console for details.</p></div>'
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
"""


def app_jsx(pages: list, use_router: bool) -> str:
    if not pages:
        return """import React from 'react'

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-lg text-neutral-600">No pages were generated.</p>
    </div>
  )
}
"""
    if not use_router or len(pages) == 1:
        page = pages[0]
        slug = page["name"].replace(" ", "")
        return f"""import React from 'react'
import {slug} from './pages/{slug}.jsx'

export default function App() {{
  return <{slug} />
}}
"""

    imports = "\n".join(
        f"import {p['name'].replace(' ', '')} from './pages/{p['name'].replace(' ', '')}.jsx'"
        for p in pages
    )
    routes = "\n      ".join(
        f"<Route path=\"{p['route']}\" element={{<{p['name'].replace(' ', '')} />}} />"
        for p in pages
    )
    return f"""import React from 'react'
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom'
{imports}

// Served from a subpath in preview (e.g. /preview/<session>/) as well as
// from the site root once actually deployed, so the router's basename is
// computed from the current location instead of being hardcoded.
const basename = window.location.pathname.replace(/[^/]*$/, '')

export default function App() {{
  return (
    <BrowserRouter basename={{basename}}>
      <Routes>
      {routes}
      </Routes>
    </BrowserRouter>
  )
}}
"""


def vite_config() -> str:
    return """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Relative base so the built app works when served from a subpath
  // (this app serves each session's build at /preview/<session_id>/,
  // not from the site root).
  base: './',
  plugins: [react()],
})
"""


def tailwind_config() -> str:
    return """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""


def postcss_config() -> str:
    return """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""


def project_readme(app_name: str, video_link_placeholder: str = "<add your demo video link here>") -> str:
    return f"""# {app_name}

Generated by FrontForge AI — a local multi-agent frontend generation system.

## Getting started

```bash
npm install
npm run dev
```

## Build for production

```bash
npm run build
```

## Notes

- All data in this app is hardcoded/mocked, per the project's frontend-only scope.
- Component colors and shapes can be changed instantly in FrontForge AI's
  Style Swapper tab without regenerating any code.
- Demo video: {video_link_placeholder}
"""
