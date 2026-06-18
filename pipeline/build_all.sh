#!/bin/zsh
# Rebuild all Form S-6 web data artifacts, in dependency order.
# Usage: ./pipeline/build_all.sh   (run from project root)
set -e
cd "$(dirname "$0")/.."
PY=./venv/bin/python3

echo "[1/6] grid.json (840 vertices)"            && $PY pipeline/build_grid.py
echo "[2/6] place names -> grid.json"            && $PY pipeline/add_place_names.py
echo "[3/6] fetch NLCD 2021 land cover"          && ./pipeline/fetch_nlcd.sh
echo "[4/6] roughness.json (NLCD z0 + log-law)"  && $PY pipeline/build_roughness.py
echo "[5/6] inputs.json (100x3 vectors)"         && $PY pipeline/read_inputs.py
echo "[6/6] powell.json (300 PDE solves ~11min)" && $PY pipeline/windfield_grid.py
echo "Done. Serve with ./start"
