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
![License](https://img.shields.io/badge/license-unspecified-lightgrey)

A standalone, offline-first course viewer for folders of exported HTML course content (e.g. Rise 360 exports). Point it at a course folder and it builds a single self-contained `index.html` reader — no web server, no framework, no external services required.

**[Live demo](https://patchamama.github.io/LearnFlow-Navigator/)** — a 3-chapter Python tutorial served as a static reader, showing the chapter timeline, navigation, and notes panel (the optional search backend needs a local server, so it isn't part of this static demo).

## Features

- **Course-style chapter timeline** — numbered nodes, completion ticks, and a collapsible course panel with **Chapters** and **Course files** tabs.
- **Automatic structure detection** — folders prefixed with a number (e.g. `01 Introduction`) become modules and expand to reveal their chapters; non-module folders and root-level `.txt`/`.md` files are grouped under **Course files**.
- **Full navigation** — First / Previous / Next / Last controls, automatic chapter completion on scroll-to-end, and light/dark themes.
- **Local notes** — Markdown edit/preview, maximize, quick task/callout insertion, `.md` import/export. Notes, theme, tasks, and completion state live only in the browser's `localStorage` and never touch the course content.
- **Optional local search backend** — a lightweight Python server adds full-text search (SQLite FTS5) over the indexed course content, with an optional multilingual semantic reranker for cross-language matching.
- **Optional AI course assistant** — ask questions about the course; answers are grounded in retrieved course excerpts (RAG-style) via Ollama, OpenAI, or Anthropic.

## Quick start

Build the reader only (creates `index.html`, no dependencies installed, no server started):

```bash
python3 course_viewer.py
```

`index.html` is created only if it doesn't already exist; otherwise a `<folder-name>.html` fallback is created instead, so a hand-edited `index.html` is never overwritten. Use `--force-index` to deliberately refresh it.

Run the builder again any time the folder structure or content changes — it embeds a fresh static manifest into the page.

## Local search backend (optional, recommended)

Use one of these launchers instead of opening `index.html` directly:

```bash
./start.sh       # Linux/macOS
start.bat        # Windows
```

They (re)build `index.html`, install `requirements.txt`, build a local SQLite course index, and start the backend at `http://localhost:8765`. When the page detects the backend it shows a **Search course** option that searches indexed content and jumps to the matching chapter.

The optional `sentence-transformers` dependency downloads the multilingual `paraphrase-multilingual-MiniLM-L12-v2` model on first indexing, enabling a compact local semantic/RAG-style reranker so questions in one supported language can match content written in another. If it can't be installed or downloaded, the SQLite FTS lexical search remains available as a fallback (without cross-language matching).

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

1. Scans the course folder for chapter HTML exports and numeric-prefixed module folders, and builds a JSON manifest of the course structure.
2. Renders a single-page HTML/CSS/JS reader with that manifest embedded, so the result is fully self-contained and works by opening the file directly.
3. Injects a small same-origin helper script (`course-reader-chapter-tools.js`) into each exported chapter so the viewer can control the embedded chapter's sidebar/navigation from the parent page.
4. Optionally serves the folder with `http.server` plus a few JSON endpoints (`/api/search`, `/api/ask`, `/api/models`, `/api/settings`) backed by a local SQLite FTS5 index, for search and the AI assistant.

See `CLAUDE.md` for a deeper architecture walkthrough.

## License

No license specified.
