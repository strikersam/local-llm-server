#!/usr/bin/env python3
"""Real-time Ollama activity monitor - shows DeepSeek 32B requests and inference"""

import requests
import json
import logging
from datetime import datetime
from threading import Thread
import time
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("ollama-monitor")

OLLAMA_BASE = "http://localhost:11434"

def monitor_ollama():
    """Monitor active models and log activity"""
    log.info("🔍 Ollama Real-Time Monitor Started")
    log.info(f"📍 Watching: {OLLAMA_BASE}")
    log.info("-" * 80)

    try:
        # Get running models
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            log.info(f"✅ Found {len(models)} model(s)")
            for m in models:
                size_gb = m.get("size", 0) / (1024**3)
                log.info(f"   • {m['name']} ({size_gb:.1f}GB)")
        log.info("-" * 80)
    except Exception as e:
        log.error(f"❌ Could not connect to Ollama: {e}")
        return

    # Monitor for activity
    log.info("🎯 Watching for DeepSeek 32B requests...\n")

    request_count = 0
    while True:
        try:
            # Simple health check - when Ollama is processing, we'll see activity
            resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1)
            if resp.status_code == 200:
                data = resp.json()
                for model in data.get("models", []):
                    if "deepseek" in model["name"].lower():
                        request_count += 1
                        expires = model.get("expires_at", "")
                        if expires:
                            log.info(f"📤 DeepSeek Activity Detected (request #{request_count})")
                            log.info(f"   Model: {model['name']}")
                            log.info(f"   Size: {model['size'] / (1024**3):.1f}GB")
                            log.info(f"   Last used: {expires}\n")

            time.sleep(0.5)  # Check twice per second
        except requests.exceptions.ConnectionError:
            log.warning("⚠️  Ollama connection lost, retrying...")
            time.sleep(2)
        except Exception as e:
            log.error(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        monitor_ollama()
    except KeyboardInterrupt:
        log.info("\n✋ Monitor stopped")
        sys.exit(0)
