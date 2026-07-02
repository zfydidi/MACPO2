#!/usr/bin/env bash
# Full build for conference_new_ready.tex (citations + cross-refs need 2--3 passes).
set -euo pipefail
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode conference_new_ready.tex
pdflatex -interaction=nonstopmode conference_new_ready.tex
pdflatex -interaction=nonstopmode conference_new_ready.tex
echo "Done: conference_new_ready.pdf"
