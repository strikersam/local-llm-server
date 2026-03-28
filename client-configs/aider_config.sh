#!/bin/bash
# Aider — connect to your home PC models (Linux/macOS/WSL)
# Usage:
#   source aider_config.sh
#   aider --model openai/deepseek-r1:671b

export OPENAI_API_BASE="https://YOUR_TUNNEL_URL/v1"
export OPENAI_API_KEY="YOUR_API_KEY"

echo "Aider configured to use home PC models."
echo "Available models:"
echo "  aider --model openai/deepseek-r1:671b"
echo "  aider --model openai/deepseek-r1:32b"
echo "  aider --model openai/qwen3-coder:30b"
