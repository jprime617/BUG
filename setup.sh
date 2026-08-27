#!/bin/bash
# Onboarding do projeto. Delega ao runner cross-platform (fonte unica: tasks.py).
set -e
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "Python nao encontrado no PATH." >&2
  exit 1
fi
exec "$PY" "$(dirname "$0")/tasks.py" setup
