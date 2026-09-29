#!/usr/bin/env bash
# One-shot installer for LearnFlow Navigator: downloads the project scripts
# from GitHub into a local folder, fetches a small Python demo course into
# examples/, then launches start.sh.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/patchamama/LearnFlow-Navigator/master/install.sh -o /tmp/learnflow-install.sh && bash /tmp/learnflow-install.sh [destination-folder]
set -euo pipefail

REPO="patchamama/LearnFlow-Navigator"
BASE="https://raw.githubusercontent.com/$REPO/master"
DEST="${1:-LearnFlow-Navigator}"

echo "Installing LearnFlow Navigator into ./$DEST ..."
mkdir -p "$DEST"
cd "$DEST"

for f in course_viewer.py course-reader-chapter-tools.js requirements.txt \
         start.sh start.bat create-index.sh create-index.bat; do
  curl -fsSL "$BASE/$f" -o "$f"
done
chmod +x start.sh create-index.sh

mkdir -p examples
curl -fsSL "$BASE/docs/01%20Introduction%20to%20Python.html" -o "examples/01 Introduction to Python.html"
curl -fsSL "$BASE/docs/02%20Variables%20and%20Data%20Types.html" -o "examples/02 Variables and Data Types.html"
curl -fsSL "$BASE/docs/03%20Control%20Flow%20and%20Functions.html" -o "examples/03 Control Flow and Functions.html"

echo "Done. Starting the course reader..."
echo "(No course content in this folder yet — when prompted, type 'examples' to open the sample Python course.)"
./start.sh
