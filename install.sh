#!/usr/bin/env bash
set -euo pipefail

# Clay CPJ CLI installer
# Usage: curl -sSf https://raw.githubusercontent.com/neomhr/clay-cpj-cli/main/install.sh | bash

CLAY_CPJ_DIR="$HOME/.clay-cpj"
OLD_CLAY_CPL_DIR="$HOME/.clay-cpl"
SRC_DIR="$CLAY_CPJ_DIR/src"
SKILL_LINK="$HOME/.claude/skills/clay-cpj"
OLD_CPL_SKILL_LINK="$HOME/.claude/skills/clay-cpl"
OLD_AUTOCLAY_SKILL_LINK="$HOME/.claude/skills/autoclay"
REPO_URL="https://github.com/neomhr/clay-cpj-cli.git"

banner() {
    echo ""
    echo "       █████  ██    ██ ████████  ██████   ██████ ██       █████  ██    ██"
    echo "      ██   ██ ██    ██    ██    ██    ██ ██      ██      ██   ██  ██  ██"
    echo "      ███████ ██    ██    ██    ██    ██ ██      ██      ███████   ████"
    echo "      ██   ██ ██    ██    ██    ██    ██ ██      ██      ██   ██    ██"
    echo "      ██   ██  ██████     ██     ██████   ██████ ███████ ██   ██    ██"
    echo ""
    echo "      Clay CPJ CLI"
    echo "      Built by Neo Mohr"
    echo ""
}

info()  { echo "  [+] $*"; }
warn()  { echo "  [!] $*" >&2; }
fail()  { echo "  [x] $*" >&2; exit 1; }

# -- Step 1: Check Python ---------------------------------------------------

find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || continue
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

banner

info "Checking for Python 3.8+..."
PYTHON=$(find_python) || {
    fail "Python 3.8+ not found. Install it first:
    macOS:   brew install python3
    Ubuntu:  sudo apt install python3 python3-pip
    Other:   https://www.python.org/downloads/"
}

PY_VER=$($PYTHON --version 2>&1)
info "Found $PY_VER ($PYTHON)"

# -- Step 2: Clone or update repo -------------------------------------------

if [ -d "$SRC_DIR/.git" ]; then
    info "Updating existing installation..."
    git -C "$SRC_DIR" pull --quiet
else
    info "Cloning Clay CPJ CLI to $SRC_DIR..."
    mkdir -p "$CLAY_CPJ_DIR"
    chmod 700 "$CLAY_CPJ_DIR"
    git clone --quiet "$REPO_URL" "$SRC_DIR"
fi

# -- Step 2b: Migrate local state from previous package names ----------------

if [ -d "$OLD_CLAY_CPL_DIR" ]; then
    info "Migrating local state from ~/.clay-cpl to ~/.clay-cpj..."
    mkdir -p "$CLAY_CPJ_DIR"
    chmod 700 "$CLAY_CPJ_DIR"
    for file in credentials.json session.json; do
        if [ -f "$OLD_CLAY_CPL_DIR/$file" ] && [ ! -f "$CLAY_CPJ_DIR/$file" ]; then
            cp -p "$OLD_CLAY_CPL_DIR/$file" "$CLAY_CPJ_DIR/$file"
            chmod 600 "$CLAY_CPJ_DIR/$file"
        fi
    done
    if [ -d "$OLD_CLAY_CPL_DIR/runs" ] && [ ! -d "$CLAY_CPJ_DIR/runs" ]; then
        cp -pR "$OLD_CLAY_CPL_DIR/runs" "$CLAY_CPJ_DIR/runs"
        chmod 700 "$CLAY_CPJ_DIR/runs"
    fi
fi

# -- Step 3: Install via pip (editable) -------------------------------------

info "Removing old package name if present..."
$PYTHON -m pip uninstall -y autoclay --quiet >/dev/null 2>&1 || true
$PYTHON -m pip uninstall -y clay-cpl --quiet >/dev/null 2>&1 || true

info "Installing clay-cpj CLI..."
$PYTHON -m pip install -e "$SRC_DIR" --quiet 2>/dev/null || \
$PYTHON -m pip install -e "$SRC_DIR" --quiet --break-system-packages 2>/dev/null || {
    fail "pip install failed. You may need to install pip:
    $PYTHON -m ensurepip --upgrade"
}

# Verify clay-cpj is on PATH
if command -v clay-cpj &>/dev/null; then
    info "clay-cpj command installed at $(command -v clay-cpj)"
else
    # pip --user install may put it in ~/.local/bin
    warn "clay-cpj is installed but not on PATH."
    warn "Add this to your shell profile:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# -- Step 4: Install Claude Code skill (global) -----------------------------

if [ -d "$HOME/.claude" ]; then
    info "Installing Claude Code skill..."
    mkdir -p "$HOME/.claude/skills"
    if [ -L "$OLD_CPL_SKILL_LINK" ]; then
        rm "$OLD_CPL_SKILL_LINK"
    fi
    if [ -L "$OLD_AUTOCLAY_SKILL_LINK" ]; then
        rm "$OLD_AUTOCLAY_SKILL_LINK"
    fi
    if [ -L "$SKILL_LINK" ] || [ -d "$SKILL_LINK" ]; then
        rm -rf "$SKILL_LINK"
    fi
    ln -s "$SRC_DIR/skill" "$SKILL_LINK"
    info "Claude Code skill linked at $SKILL_LINK"
else
    info "Claude Code not detected (~/.claude/ not found). Skipping skill install."
    info "To install later: ln -s $SRC_DIR/skill ~/.claude/skills/clay-cpj"
fi

# -- Step 5: Prompt for setup -----------------------------------------------

echo ""
echo "  ─── Installation complete! ───"
echo ""
echo "  Next step: run 'clay-cpj setup' to configure your Clay credentials."
echo ""
echo "  To update later: clay-cpj update"
echo ""
