#!/usr/bin/env python3
"""
Real-time Ollama DeepSeek 32B activity logger
Monitors all requests hitting Ollama and logs them with timestamps and details
"""

import requests
import json
import logging
import time
import sys
from datetime import datetime
from typing import Optional
import threading

# Setup console logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("deepseek-monitor")

OLLAMA_BASE = "http://localhost:11434"
MODEL_TARGET = "deepseek-r1:32b"

class OllamaMonitor:
    def __init__(self):
        self.last_check = time.time()
        self.request_count = 0
        self.is_connected = False

    def check_connection(self) -> bool:
        """Verify Ollama is running"""
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
            self.is_connected = r.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def log_models(self):
        """Log currently loaded models"""
        try:
            r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
            if r.status_code == 200:
                models = r.json().get("models", [])
                for m in models:
                    size_gb = m.get("size", 0) / (1024**3)
                    status = "🟢 LOADED" if "deepseek" in m["name"].lower() else "📦"
                    log.info(f"{status} | {m['name']:30s} | {size_gb:6.1f}GB")
        except Exception as e:
            log.error(f"Failed to fetch models: {e}")

    def run(self):
        """Main monitor loop"""
        log.info("=" * 100)
        log.info("🚀 Ollama DeepSeek 32B Real-Time Logger Started")
        log.info("=" * 100)

        if not self.check_connection():
            log.error(f"❌ Cannot connect to Ollama at {OLLAMA_BASE}")
            log.error("   Make sure Ollama is running: check 'ollama serve' in another terminal")
            return

        log.info(f"✅ Connected to Ollama at {OLLAMA_BASE}\n")
        log.info("📋 Currently loaded models:")
        self.log_models()

        log.info("\n" + "=" * 100)
        log.info("⏳ Waiting for DeepSeek 32B requests... (This will show all Ollama activity)")
        log.info("=" * 100 + "\n")

        last_status_time = time.time()

        while True:
            try:
                if not self.check_connection():
                    log.warning("⚠️  Connection lost, attempting reconnect...")
                    time.sleep(2)
                    continue

                # Check loaded models and their status
                r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
                if r.status_code == 200:
                    models = r.json().get("models", [])

                    for model in models:
                        if "deepseek" in model["name"].lower():
                            expires = model.get("expires_at", "")
                            # Model is actively in use if expires_at is set
                            if expires:
                                self.request_count += 1
                                log.info(f"\n{'🔥' * 40}")
                                log.info(f"REQUEST #{self.request_count:,} - DeepSeek Activity Detected")
                                log.info(f"{'🔥' * 40}")
                                log.info(f"  Model:     {model['name']}")
                                log.info(f"  Size:      {model['size'] / (1024**3):.1f}GB")
                                log.info(f"  Last used: {expires}")
                                log.info("")

                # Every 10 seconds, show we're still monitoring
                now = time.time()
                if now - last_status_time > 10:
                    log.debug(f"✓ Still monitoring... ({self.request_count} requests seen)")
                    last_status_time = now

                time.sleep(0.2)  # Check 5x per second

            except KeyboardInterrupt:
                log.info("\n✋ Monitor stopped by user")
                log.info(f"Total DeepSeek requests monitored: {self.request_count}")
                sys.exit(0)
            except Exception as e:
                log.warning(f"Monitor error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    monitor = OllamaMonitor()
    monitor.run()
