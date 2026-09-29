@echo off
setlocal EnableExtensions
REM One-shot installer for LearnFlow Navigator: downloads the project scripts
REM from GitHub into a local folder, fetches a small Python demo course into
REM examples\, then launches start.bat.
REM
REM Usage:
REM   curl -fsSL -o install.bat https://raw.githubusercontent.com/patchamama/LearnFlow-Navigator/master/install.bat && install.bat [destination-folder]

set "REPO=patchamama/LearnFlow-Navigator"
set "BASE=https://raw.githubusercontent.com/%REPO%/master"
set "DEST=%~1"
if "%DEST%"=="" set "DEST=LearnFlow-Navigator"

echo Installing LearnFlow Navigator into .\%DEST% ...
mkdir "%DEST%" 2>nul
pushd "%DEST%"

for %%F in (course_viewer.py course-reader-chapter-tools.js requirements.txt start.sh start.bat create-index.sh create-index.bat) do (
  curl -fsSL "%BASE%/%%F" -o "%%F"
)

mkdir examples 2>nul
curl -fsSL "%BASE%/docs/01%%20Introduction%%20to%%20Python.html" -o "examples\01 Introduction to Python.html"
curl -fsSL "%BASE%/docs/02%%20Variables%%20and%%20Data%%20Types.html" -o "examples\02 Variables and Data Types.html"
curl -fsSL "%BASE%/docs/03%%20Control%%20Flow%%20and%%20Functions.html" -o "examples\03 Control Flow and Functions.html"

echo Done. Starting the course reader...
echo (No course content in this folder yet -- when prompted, type "examples" to open the sample Python course.)
call start.bat
popd
