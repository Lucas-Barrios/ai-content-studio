#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="venv"
PYTHON="${PYTHON:-python3}"

echo "=== AI Content Studio — Setup ==="
echo ""

# ── 1. Check Python ────────────────────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
  echo "ERROR: python3 not found. Install it from https://python.org and retry."
  exit 1
fi

PYTHON_VERSION=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Using Python $PYTHON_VERSION  ($($PYTHON -c 'import sys; print(sys.executable)'))"

# ── 2. Create virtual environment ──────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
  echo "Virtual environment '$VENV_DIR/' already exists — skipping creation."
else
  echo "Creating virtual environment in '$VENV_DIR/'..."
  "$PYTHON" -m venv "$VENV_DIR"
  echo "Done."
fi

# ── 3. Install dependencies ────────────────────────────────────────────────────
echo ""
echo "Installing dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt
echo "Done."

# ── 4. Create .env if missing ──────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "Created .env from .env.example — add your API keys before running the app."
fi

# ── 5. Next steps ──────────────────────────────────────────────────────────────
echo ""
echo "=== Setup complete ==="
echo ""
echo "Activate the virtual environment with:"
echo ""
if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32" ]]; then
  echo "    .\\venv\\Scripts\\activate"
else
  echo "    source venv/bin/activate"
fi
echo ""
echo "Then run the app:"
echo "    python -m src.main --refresh-kb"
echo "    python -m src.main --type blog_post --topic \"Your topic\" --audience \"Your audience\""
echo ""
