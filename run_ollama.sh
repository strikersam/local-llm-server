#!/usr/bin/env bash
# Starts Ollama with the configured model directory.
# Source .env before running, or set OLLAMA_MODELS in your environment.

set -e

OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

export OLLAMA_MODELS OLLAMA_HOST

OLLAMA_EXE="${OLLAMA_EXE:-ollama}"
exec "$OLLAMA_EXE" serve
