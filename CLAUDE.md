# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A standalone, offline-first course viewer ("LearnFlow Navigator") for a folder of exported Rise 360 HTML chapters (the "ELO 25 Flows Development" course). `course_viewer.py` scans the current folder, embeds a static manifest of chapters/modules/files into a single self-contained `index.html`, and optionally runs a tiny local Python backend that adds full-text/semantic search and an "ask AI about this course" feature. There is no build system, framework, or package manifest beyond `requirements.txt` — this is plain Python 3 stdlib + one optional dependency, and vanilla JS/CSS inlined into the generated HTML.

## Commands

Build the static viewer only (no server, no deps installed):
```bash
python3 course_viewer.py            # creates index.html if missing, else <folder-name>.html
python3 course_viewer.py --force-index   # explicitly overwrite index.html
./create-index.sh                   # == start.sh --build-only
create-index.bat                    # Windows equivalent
```

Build + install deps + serve with local search backend on `http://localhost:8765`:
```bash
./start.sh              # Linux/macOS, installs requirements.txt (sentence-transformers) by default
start.bat                # Windows, creates a local .venv first to avoid long-path issues
start.sh --build-only    # build index.html only, skip serving
```
Both launchers auto-download a local Python if none is found on PATH.

There is no test suite, linter, or formatter configured in this repo — there is nothing to run beyond the commands above.

## Architecture

Everything server/build-side lives in one file, `course_viewer.py` (stdlib only: `http.server`, `sqlite3`, `html.parser`, `urllib.request`):

- **`course_data()` / `is_module()` / `chapter_title()`** — scans `ROOT` for `*.html` chapter exports and numeric-prefixed folders (e.g. `01 Introduction`) which are treated as modules; builds the JSON manifest (`chapters`, `modules`, `courseFiles`) embedded into the generated page. Folder/file naming conventions (numeric prefix = module, `.md`/`.txt` at root = course files) drive the whole UI structure — there's no config file for this.
- **`build()` / `output_path()`** — renders the `APP` template (a single big HTML/CSS/JS string constant with `__DATA__` replaced by the JSON manifest) to `index.html`. Never overwrites an existing `index.html` unless `--force-index` is passed; otherwise falls back to `<folder-name>.html`. This is a deliberate safeguard against clobbering a hand-tweaked `index.html`.
- **`inject_chapter_tools()`** — injects a `<script src="course-reader-chapter-tools.js">` tag into every exported chapter HTML file (idempotent, checked via a `data-course-reader-tools="1"` marker). `course-reader-chapter-tools.js` runs *inside* each Rise 360 chapter iframe and lets the parent viewer hide Rise's own sidebar and hijack in-course nav links via `postMessage`.
- **`build_search_index()` / `search_course()`** — strips chapter HTML to plain text (`TextExtractor`), chunks it, and stores it in `course_index.sqlite` using FTS5 for lexical search. If `sentence-transformers` (multilingual MiniLM) is installed, it also stores embeddings and reranks results semantically/cross-lingually; otherwise it silently falls back to FTS5-only. Both code paths must keep working — the semantic dependency is optional by design (see README's "Local search backend" section).
- **`CourseHandler` (`SimpleHTTPRequestHandler`)** — serves the folder as static files and adds JSON endpoints: `/api/search`, `/api/models`, `/api/ask` (RAG-style: retrieves via `search_course()` then calls the configured LLM provider), `/api/settings` (persists AI provider/key to `.course-reader-settings.json`, gitignored), `/api/reindex`, `/api/health`.
- **`provider_request()` / `provider_models()` / `ask_course()`** — thin adapters for Ollama (local), OpenAI, and Anthropic; add new providers here and in the frontend `<select id="provider">` together.

The frontend (inside the `APP` string) is a single-page app with no external assets: it renders the chapter tree from the embedded manifest, drives chapter navigation inside an `<iframe>`, and stores progress/notes/theme/AI settings client-side in `localStorage` (namespaced keys like `course-reader-v2`, `course-reader-ai-v1`, `course-reader-positions`) — content files themselves are never modified by user progress/notes.

## Conventions worth knowing before editing

- `course_viewer.py` is intentionally terse/dense (short functions, inline comments only where behavior is non-obvious — e.g. why `index.html` is protected, why the semantic path is wrapped in `try/except`). Match that style rather than expanding it into a package.
- The exported course chapter HTML files (`NN Title - ... _ Rise 360.html`) and the `resources/` folder are generated/source course content, not application code — they're gitignored (see `.gitignore`) and should not be treated as things to refactor.
- `.course-reader-settings.json`, `course_index.sqlite`, `.venv/`, `.python*/` are local runtime state, also gitignored — never assume they exist or commit them.
