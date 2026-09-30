# LearnFlow Navigator

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Stdlib only](https://img.shields.io/badge/dependencies-stdlib%20only-informational)
![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E?logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)
![SQLite FTS5](https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-optional-yellow)
![Ollama](https://img.shields.io/badge/Ollama-local-000000)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-API-D97757)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A standalone, offline-first course viewer for folders of exported HTML course content (e.g. Rise 360 exports). Point it at a course folder and it builds a single self-contained `index.html` reader — no web server, no framework, no external services required.

The project started with a simple goal: present web pages saved with the **Save Page WE** browser extension (Chrome and Firefox add-on that saves a complete web page as a single, self-contained HTML file) as a navigable, course-style reader. Rise 360 exports, Markdown chapters, and search grew on top of that.

**[Live demo](https://patchamama.github.io/LearnFlow-Navigator/)** — a Python tutorial served as a static reader: three HTML chapters plus a Markdown chapter showing off syntax-highlighted code blocks, chapter timeline, navigation, and notes panel. Search works there too — no backend is running, so it falls back to an in-browser, case-insensitive search across chapter text.

## Install

Downloads the scripts from this repository into a local folder, drops a small Python-tutorial demo into `examples/`, and starts the reader — one line, no `git clone` needed:

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/patchamama/LearnFlow-Navigator/master/install.sh -o /tmp/learnflow-install.sh && bash /tmp/learnflow-install.sh
```

```bat
:: Windows (cmd)
curl -fsSL -o install.bat https://raw.githubusercontent.com/patchamama/LearnFlow-Navigator/master/install.bat && install.bat
```

Both install into `./LearnFlow-Navigator` by default (pass a folder name as an argument to change that) and finish by running `start.sh`/`start.bat`. If the folder you land in has no course content yet, the reader will ask for one — type `examples` to open the bundled demo.

## Features

- **Course-style chapter timeline** — numbered nodes, completion ticks, and a collapsible course panel with **Chapters** and **Course files** tabs.
- **Automatic structure detection** — folders prefixed with a number (e.g. `01 Introduction`) become modules and expand to reveal their chapters; non-module folders and root-level `.txt` files are grouped under **Course files**.
- **Markdown chapters** — drop a `.md` file anywhere a `.html` chapter could go (root or inside a numbered module) and it becomes a chapter too, numbered and titled the same way. It's rendered client-side, with syntax highlighting for fenced code blocks (`python`, `php`, `java`, `go`, `javascript`, `xml`, `html`, `json`, `bash`, …) — no backend needed.
- **Full navigation** — First / Previous / Next / Last controls, automatic chapter completion on scroll-to-end, and a light/dark theme that also follows your system preference for content pages (including the bundled Python demo chapters).
- **Local notes** — Markdown edit/preview, maximize, quick task/callout insertion, `.md` import/export. Notes, theme, tasks, and completion state live only in the browser's `localStorage` and never touch the course content.
- **Search, with or without a backend** — with the local backend running, search uses SQLite FTS5 plus an optional multilingual semantic reranker for cross-language matching. Without a backend (e.g. this project's own GitHub Pages demo, or `index.html` opened directly), search automatically falls back to an in-browser, case-insensitive scan of each chapter's text.
- **Optional AI course assistant** — ask questions about the course; answers are grounded in retrieved course excerpts (RAG-style) via Ollama, OpenAI, or Anthropic. Requires the local backend.

## Quick start

Build the reader only (creates `index.html`, no dependencies installed, no server started):

```bash
python3 course_viewer.py
```

`index.html` is created only if it doesn't already exist; otherwise a `<folder-name>.html` fallback is created instead, so a hand-edited `index.html` is never overwritten. Use `--force-index` to deliberately refresh it.

Run the builder again any time the folder structure or content changes — it embeds a fresh static manifest into the page.

### Building a course in a specific folder

Pass a folder as the first argument to build/serve a course anywhere on disk, instead of wherever `course_viewer.py` itself lives. The folder is created if it doesn't exist yet, so this also works for starting a brand-new course from scratch:

```bash
python3 course_viewer.py ./my-course --force-index
./start.sh ./my-course        # same, but also serves it with search
start.bat my-course
```

If you run the tool with no folder argument and the current folder has no chapters, it asks which folder to use instead of silently building an empty reader:

```
No course chapters found in '/path/to/LearnFlow-Navigator'.
Enter a folder to use instead (e.g. examples), or press Enter to keep this one:
```

## Local search backend (optional, recommended)

Use one of these launchers instead of opening `index.html` directly:

```bash
./start.sh       # Linux/macOS
start.bat        # Windows
```

They (re)build `index.html`, install `requirements.txt`, build a local SQLite course index, and start the backend at `http://localhost:8765`.

The optional `sentence-transformers` dependency downloads the multilingual `paraphrase-multilingual-MiniLM-L12-v2` model on first indexing, enabling a compact local semantic/RAG-style reranker so questions in one supported language can match content written in another. If it can't be installed or downloaded, the SQLite FTS lexical search remains available as a fallback (without cross-language matching).

**Without this backend** — opening `index.html` directly, or a static deployment like GitHub Pages — the **Search course** option still works: it fetches each chapter's own content in the browser and does a case-insensitive text search across them, showing the matching snippet. It's plain substring matching, not semantic, and needs the chapters to be reachable over `http(s)` (a bare `file://` open can't `fetch()` sibling files, so search has nothing to read from in that specific case).

`start.bat` / `start.sh` use only the Python standard library by default. Add `--semantic` to also install the optional multilingual embedding dependency:

```bash
start.bat --semantic
```

### Build index only

Create or refresh only `index.html`, without installing packages or starting the backend:

```bash
./create-index.sh
```

```bat
create-index.bat
```

## AI course assistant (optional)

In **Settings**, choose a provider (Ollama, OpenAI, or Anthropic) and an API key/model. Enabling **Save this configuration and API key in the local backend** persists the provider, model, course language, and key to `.course-reader-settings.json` in the course folder — convenient for a personal offline folder, but stored as plain text, so avoid this in shared folders or committing it to version control. Without this option, configuration stays only in browser local storage.

## Windows notes

`start.bat` creates and uses a project-local `.venv`, avoiding long `AppData` paths that can break dependency installation, and installs with `--no-cache-dir`. If the optional semantic package still fails to install, it warns and starts the viewer with the SQLite FTS fallback rather than stopping.

## How it works

`course_viewer.py` is a single Python stdlib script (only optional dependency: `sentence-transformers`) that:

1. Scans the course folder for chapter HTML/Markdown exports and numeric-prefixed module folders, and builds a JSON manifest of the course structure.
2. Renders a single-page HTML/CSS/JS reader with that manifest embedded, so the result is fully self-contained and works by opening the file directly.
3. Injects a small same-origin helper script (`course-reader-chapter-tools.js`) into each exported HTML chapter so the viewer can control the embedded chapter's sidebar/navigation from the parent page. Markdown chapters don't need this — they're fetched and rendered client-side into the reader's iframe, with syntax highlighting for fenced code blocks.
4. Optionally serves the folder with `http.server` plus a few JSON endpoints (`/api/search`, `/api/ask`, `/api/models`, `/api/settings`) backed by a local SQLite FTS5 index, for search and the AI assistant. Without that backend, the frontend searches chapter text itself instead of showing an error.

See `CLAUDE.md` for a deeper architecture walkthrough.

## License

[MIT](LICENSE)
