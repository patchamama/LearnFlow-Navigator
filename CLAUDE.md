# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A standalone, offline-first course viewer ("LearnFlow Navigator") for a folder of exported Rise 360 HTML chapters (the "ELO 25 Flows Development" course). `course_viewer.py` scans the current folder, embeds a static manifest of chapters/modules/files into a single self-contained `index.html`, and optionally runs a tiny local Python backend that adds full-text/semantic search and an "ask AI about this course" feature. There is no build system, framework, or package manifest beyond `requirements.txt` — this is plain Python 3 stdlib + one optional dependency, and vanilla JS/CSS inlined into the generated HTML.

## Commands

Build the static viewer only (no server, no deps installed):
```bash
python3 course_viewer.py            # creates index.html if missing, else <folder-name>.html
python3 course_viewer.py --force-index   # explicitly overwrite index.html
python3 course_viewer.py ./some-folder --force-index   # target a different course folder (created if missing)
./create-index.sh                   # == start.sh --build-only
create-index.bat                    # Windows equivalent
```

Build + serve with local search backend on `http://localhost:8765`:
```bash
./start.sh                     # Linux/macOS, stdlib only by default
start.bat                      # Windows, creates a local .venv first to avoid long-path issues
start.sh --semantic            # also install sentence-transformers for cross-language search
start.sh --build-only          # build index.html only, skip serving
start.sh ./some-folder         # any of the above, targeting a different course folder
```
Both launchers auto-download a local Python if none is found on PATH. A first positional argument (not starting with `--`) is always forwarded to `course_viewer.py` as the target folder.

`install.sh` / `install.bat` bootstrap all of the above from scratch on a machine with nothing cloned yet: they curl the scripts from `raw.githubusercontent.com`, fetch the `docs/` demo into `examples/`, and run `start.sh`/`start.bat`. See the README's "Install" section for the one-line commands.

There is no test suite, linter, or formatter configured in this repo — there is nothing to run beyond the commands above.

## Architecture

Everything server/build-side lives in one file, `course_viewer.py` (stdlib only: `http.server`, `sqlite3`, `html.parser`, `urllib.request`):

- **`ROOT` / `SCRIPT_DIR` / `set_root()`** — `SCRIPT_DIR` is fixed (where `course_viewer.py` itself lives); `ROOT` is the course folder being built/served and is mutable — it starts equal to `SCRIPT_DIR` but `set_root()` repoints it (and recomputes `GENERATED_NAMES`) when a folder argument is passed on the CLI, or when the "no chapters found" interactive prompt picks a different folder. Every function below reads the *global* `ROOT` at call time, so `set_root()` must run before any scanning/building happens.
- **`course_data()` / `is_module()` / `chapter_title()`** — scans `ROOT` for `*.html` chapter exports and numeric-prefixed folders (e.g. `01 Introduction`) which are treated as modules; builds the JSON manifest (`chapters`, `modules`, `courseFiles`) embedded into the generated page. Folder/file naming conventions (numeric prefix = module, `.md`/`.txt` at root = course files) drive the whole UI structure — there's no config file for this.
- **`build()` / `output_path()`** — renders the `APP` template (a single big HTML/CSS/JS string constant with `__DATA__` replaced by the JSON manifest) to `index.html`. Never overwrites an existing `index.html` unless `--force-index` is passed; otherwise falls back to `<folder-name>.html`. This is a deliberate safeguard against clobbering a hand-tweaked `index.html`.
- **`inject_chapter_tools()` / `ensure_chapter_tools_asset()`** — injects a `<script src="course-reader-chapter-tools.js">` tag into every exported chapter HTML file (idempotent, checked via a `data-course-reader-tools="1"` marker), copying that JS file from `SCRIPT_DIR` into `ROOT` first if the two differ (i.e. `ROOT` is some other course folder). `course-reader-chapter-tools.js` runs *inside* each Rise 360 chapter iframe and lets the parent viewer hide Rise's own sidebar and hijack in-course nav links via `postMessage`.
- **`build_search_index()` / `search_course()` / `semantic_model()`** — strips chapter HTML to plain text (`TextExtractor`), chunks it, and stores it in `course_index.sqlite` using FTS5 for lexical search. If `sentence-transformers` (multilingual MiniLM, lazily loaded once via `semantic_model()`) is available, chunk embeddings are also stored. `search_course()` scores *every* stored embedding against the query (not just the lexical FTS hits) and merges those semantic hits with the lexical ones — retrieval must stay semantic-first for cross-language queries to work at all, since a query sharing no words with the course text would otherwise never reach the reranker. Both the lexical-only and semantic-augmented paths must keep working — the semantic dependency is optional by design (see README's "Local search backend" section).
- **`CourseHandler` (`SimpleHTTPRequestHandler`)** — serves `ROOT` as static files (via `functools.partial(CourseHandler, directory=str(ROOT))`, not `cwd` — required now that `ROOT` can differ from the script's own folder) and adds JSON endpoints: `/api/search`, `/api/models`, `/api/ask` (RAG-style: retrieves via `search_course()` then calls the configured LLM provider), `/api/settings` (persists AI provider/key to `.course-reader-settings.json`, gitignored), `/api/reindex`, `/api/health`. `serve()` binds to `127.0.0.1` only — `/api/settings` returns the saved provider API key in plaintext with no auth, so this must never bind to all interfaces.
- **`provider_request()` / `provider_models()` / `ask_course()`** — thin adapters for Ollama (local), OpenAI, and Anthropic; add new providers here and in the frontend `<select id="provider">` together.

The frontend (inside the `APP` string) is a single-page app with no external assets: it renders the chapter tree from the embedded manifest, drives chapter navigation inside an `<iframe>`, and stores progress/notes/theme/AI settings client-side in `localStorage` (namespaced keys like `course-reader-v2`, `course-reader-ai-v1`, `course-reader-positions`) — content files themselves are never modified by user progress/notes.

## Conventions worth knowing before editing

- `course_viewer.py` is intentionally terse/dense (short functions, inline comments only where behavior is non-obvious — e.g. why `index.html` is protected, why the semantic path is wrapped in `try/except`). Match that style rather than expanding it into a package.
- The exported course chapter HTML files (`NN Title - ... _ Rise 360.html`) and the `resources/` folder are generated/source course content, not application code — they're gitignored (see `.gitignore`) and should not be treated as things to refactor.
- `docs/` is the opposite case: it's a real, committed 3-chapter Python-tutorial demo (built with this project's own `course_viewer.py`) served via GitHub Pages and linked from the README. The root `.gitignore`'s `*.html` rule has a `!docs/*.html` exception for it — remember that exception if the ignore rules ever change, or the demo's chapter pages silently stop being tracked again (this happened once; see git history).
- `.course-reader-settings.json`, `course_index.sqlite`, `.venv/`, `.python*/` are local runtime state, also gitignored — never assume they exist or commit them.
- `install.sh` / `install.bat` fetch files from `raw.githubusercontent.com/patchamama/LearnFlow-Navigator/master/...`; any file they reference (the core scripts plus the three `docs/*.html` demo chapters, fetched with `%20`-escaped spaces) must stay at that path and branch, or the installer breaks silently for anyone running the README one-liner.
