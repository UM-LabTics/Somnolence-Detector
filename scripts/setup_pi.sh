#!/usr/bin/env bash
# setup_pi.sh — idempotent setup for the Somnolence Detector on Raspberry Pi 5.
#
# Addresses the pi_setup_progress.md blocker: Debian Trixie ships Python 3.13,
# but MediaPipe has no aarch64 wheels for 3.13. We install Python 3.12 via
# pyenv and create the detector venv against it.
#
# Usage:
#     bash scripts/setup_pi.sh                # set up venv + base deps
#     YOLO=1 bash scripts/setup_pi.sh         # also install ncnn for YOLO
#     RECREATE=1 bash scripts/setup_pi.sh     # wipe and recreate the venv
#
# Safe to re-run: each step detects existing state.
set -euo pipefail

PY_REQUIRED="3.12.7"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DETECTOR_DIR="$REPO_ROOT/detector"
VENV_DIR="$DETECTOR_DIR/venv"
PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"

log() { printf "\033[36m[setup_pi]\033[0m %s\n" "$*"; }
warn() { printf "\033[33m[setup_pi]\033[0m %s\n" "$*" >&2; }
die() { printf "\033[31m[setup_pi]\033[0m %s\n" "$*" >&2; exit 1; }

log "Repo:     $REPO_ROOT"
log "Detector: $DETECTOR_DIR"

# ------------------------------------------------------------------
# 1. OS packages needed to compile Python and build MediaPipe wheels.
# ------------------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
    log "Installing OS build dependencies (may prompt for sudo)"
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends \
        build-essential git curl ca-certificates \
        libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
        libffi-dev liblzma-dev \
        libgl1 libglib2.0-0 v4l-utils
else
    warn "apt-get not found — skipping OS package install. Make sure build tools are present."
fi

# ------------------------------------------------------------------
# 2. Python 3.12 via pyenv (only if system Python isn't already 3.12.x).
# ------------------------------------------------------------------
TARGET_PY=""
SYS_PY_VER="$(python3 --version 2>&1 | awk '{print $2}' || echo "")"
log "System python3 reports: ${SYS_PY_VER:-none}"

if [[ "$SYS_PY_VER" == 3.12.* ]]; then
    log "System Python 3.12 is fine — skipping pyenv"
    TARGET_PY="$(command -v python3)"
else
    if [[ ! -d "$PYENV_ROOT" ]]; then
        log "Installing pyenv into $PYENV_ROOT"
        curl -fsSL https://pyenv.run | bash
    else
        log "pyenv already present at $PYENV_ROOT"
    fi

    export PYENV_ROOT
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"

    if ! pyenv versions --bare | grep -qx "$PY_REQUIRED"; then
        log "Compiling Python $PY_REQUIRED via pyenv (15-30 min on a Pi 5)"
        pyenv install "$PY_REQUIRED"
    else
        log "Python $PY_REQUIRED already built by pyenv"
    fi

    TARGET_PY="$PYENV_ROOT/versions/$PY_REQUIRED/bin/python3"

    # Make pyenv persistent for interactive shells. Idempotent: only adds once.
    BASHRC="$HOME/.bashrc"
    if [[ -f "$BASHRC" ]] && ! grep -q 'pyenv init' "$BASHRC"; then
        log "Appending pyenv init to $BASHRC"
        {
            echo ''
            echo '# pyenv (added by setup_pi.sh)'
            echo 'export PYENV_ROOT="$HOME/.pyenv"'
            echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
            echo 'eval "$(pyenv init -)"'
        } >> "$BASHRC"
    fi
fi

[[ -x "$TARGET_PY" ]] || die "Target Python not executable: $TARGET_PY"
log "Using Python: $TARGET_PY ($("$TARGET_PY" --version))"

# ------------------------------------------------------------------
# 3. Detector venv.
# ------------------------------------------------------------------
if [[ "${RECREATE:-0}" == "1" && -d "$VENV_DIR" ]]; then
    log "RECREATE=1 — removing existing $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating venv at $VENV_DIR"
    "$TARGET_PY" -m venv "$VENV_DIR"
else
    log "venv already exists — reusing"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel

# ------------------------------------------------------------------
# 4. Detector dependencies.
# ------------------------------------------------------------------
log "Installing requirements (mediapipe, opencv, paho-mqtt, numpy)"
# Install base deps explicitly so a missing ncnn wheel does not fail the whole run.
python -m pip install \
    "mediapipe>=0.10.14" \
    "opencv-python>=4.9.0" \
    "numpy>=1.26,<2.1" \
    "paho-mqtt==2.1.0"

if [[ "${YOLO:-0}" == "1" ]]; then
    log "YOLO=1 — installing ncnn"
    if ! python -m pip install "ncnn>=1.0.20240820"; then
        warn "ncnn install failed. If there is no prebuilt wheel for aarch64, "
        warn "you may need to build ncnn from source. The detector will still run "
        warn "without YOLO as long as YOLO_ENABLED is not set to true."
    fi
fi

# ------------------------------------------------------------------
# 5. Smoke tests.
# ------------------------------------------------------------------
log "Smoke-testing imports"
python - <<'PY'
import sys
print(f"python: {sys.version}")
import mediapipe, cv2, numpy, paho.mqtt.client as _
print(f"mediapipe: {mediapipe.__version__}")
print(f"opencv:    {cv2.__version__}")
print(f"numpy:     {numpy.__version__}")
try:
    import ncnn
    print("ncnn:      installed")
except ImportError:
    print("ncnn:      not installed (YOLO feature will be disabled)")
PY

log "Verifying webcam device"
if [[ -e /dev/video0 ]]; then
    log "/dev/video0 present"
else
    warn "/dev/video0 NOT present — plug in a USB webcam before running the detector"
fi

log "Done. Next steps:"
echo "  source $VENV_DIR/bin/activate"
echo "  export MQTT_BROKER=<ip-of-the-mac>       # e.g. 192.168.50.93"
echo "  export YOLO_ENABLED=true                 # optional, needs models/ and ncnn"
echo "  python $DETECTOR_DIR/main.py             # add --no-display on a headless Pi"
