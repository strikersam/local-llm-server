#!/usr/bin/env bash
# Local LLM Server - One-Time Setup (Linux/macOS)
# Installs Python dependencies and cloudflared.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================="
echo " Local LLM Server -- One-Time Setup"
echo "======================================================="

# -- Step 1: Python dependencies -----------------------------------------------
echo ""
echo "[1/3] Installing Python dependencies..."

PYTHON_EXE="${PYTHON_EXE:-python3}"
if ! command -v "$PYTHON_EXE" &>/dev/null; then
    echo "[FAIL] Python 3 not found."
    echo "  macOS:  brew install python"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi

"$PYTHON_EXE" -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "[OK] Python dependencies installed ($("$PYTHON_EXE" --version))"

# -- Step 2: Install cloudflared -----------------------------------------------
echo ""
echo "[2/3] Installing cloudflared..."

if command -v cloudflared &>/dev/null; then
    echo "[OK] Already installed: $(cloudflared --version)"
else
    OS="$(uname -s)"
    ARCH="$(uname -m)"

    if [[ "$OS" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install cloudflare/cloudflare/cloudflared
        else
            echo "[FAIL] Homebrew not found. Install from https://brew.sh then re-run."
            exit 1
        fi
    elif [[ "$OS" == "Linux" ]]; then
        if [[ "$ARCH" == "x86_64" ]]; then
            CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        elif [[ "$ARCH" == "aarch64" ]]; then
            CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        else
            echo "[FAIL] Unsupported arch: $ARCH"
            exit 1
        fi
        sudo curl -fsSL "$CF_URL" -o /usr/local/bin/cloudflared
        sudo chmod +x /usr/local/bin/cloudflared
    else
        echo "[FAIL] Unsupported OS: $OS. Install cloudflared manually from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        exit 1
    fi
    echo "[OK] cloudflared installed: $(cloudflared --version)"
fi

# -- Step 3: Tunnel setup -------------------------------------------------------
echo ""
echo "[3/3] Cloudflare Tunnel Setup"
echo ""
echo "Choose tunnel type:"
echo "  [1] Quick Tunnel  -- No account needed. URL changes every restart."
echo "  [2] Named Tunnel  -- Requires free Cloudflare account. Permanent URL."
echo ""
read -rp "Enter 1 or 2 (default: 1): " choice

if [[ "$choice" == "2" ]]; then
    echo ""
    echo "  Step 1: Login to Cloudflare (opens browser)..."
    cloudflared tunnel login

    TUNNEL_NAME="local-llm-server"
    echo "  Step 2: Creating named tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create "$TUNNEL_NAME"

    echo ""
    read -rp "  Domain (e.g. llm.yourdomain.com) or Enter to skip: " domain
    if [[ -n "$domain" ]]; then
        cloudflared tunnel route dns "$TUNNEL_NAME" "$domain"
        echo "[OK] DNS route: $domain -> tunnel"
        echo "TUNNEL_DOMAIN=$domain" >> "$SCRIPT_DIR/.env"
    fi
    echo "[OK] Named tunnel '$TUNNEL_NAME' created."
else
    echo "[OK] Quick tunnel selected. URL shown at server startup."
fi

# -- Make scripts executable ---------------------------------------------------
chmod +x "$SCRIPT_DIR"/*.sh

echo ""
echo "======================================================="
echo " Setup Complete!"
echo "======================================================="
echo " Start:  ./start_server.sh"
echo " Stop:   ./stop_server.sh"
echo " Config: .env"
echo "======================================================="
