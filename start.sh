#!/usr/bin/env bash
set -euo pipefail
ORIG_PWD="$PWD"
MODE="serve"
SEMANTIC="false"
FOLDER=""
for arg in "$@"; do
  case "$arg" in
    --build-only) MODE="build" ;;
    --semantic) SEMANTIC="true" ;;
    --*) ;;
    *) FOLDER="$arg" ;;
  esac
done
if [[ -n "$FOLDER" && "$FOLDER" != /* ]]; then
  FOLDER="$ORIG_PWD/$FOLDER"
fi
cd "$(dirname "$0")"
PY=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
if [[ -z "$PY" ]]; then
  echo "Python was not found. Downloading a local Python build…"
  mkdir -p .python-src
  curl -L --fail https://www.python.org/ftp/python/3.12.10/Python-3.12.10.tgz -o /tmp/python.tgz
  tar -xzf /tmp/python.tgz -C .python-src --strip-components=1
  (cd .python-src && ./configure --prefix="$PWD/../.python" --with-ensurepip=install && make -j2 install)
  PY="$PWD/.python/bin/python3"
fi
if [[ "$MODE" == "build" ]]; then
  "$PY" course_viewer.py --force-index ${FOLDER:+"$FOLDER"}
  exit 0
fi
if [[ "$SEMANTIC" == "true" ]]; then
  "$PY" -m pip install --no-cache-dir -r requirements.txt || echo "Semantic model unavailable; SQLite FTS fallback remains active."
fi
"$PY" course_viewer.py --force-index --serve --port 8765 ${FOLDER:+"$FOLDER"}
