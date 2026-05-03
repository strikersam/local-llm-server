#!/usr/bin/env python3
"""
Setup wizard for local-llm-server.
Scans local models, configures services, and starts the proxy.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional
import platform

class LocalLLMSetup:
    def __init__(self):
        self.repo_path = Path.cwd()
        self.models_path: Optional[Path] = None
        self.local_models = []
        self.config = {}

    def welcome(self):
        """Show welcome screen."""
        print("\n" + "="*60)
        print("🚀 Local LLM Server Setup Wizard")
        print("="*60)
        print("\nThis wizard will:")
        print("  1. Scan for local models")
        print("  2. Configure the proxy")
        print("  3. Start the services")
        print()

    def find_local_models(self):
        """Scan for local models."""
        print("\n📁 Scanning for local models...")

        # First, check if there's already a models folder specified
        default_models_path = Path.home() / "Desktop/Syncthing/local-models"

        while True:
            models_path_input = input(
                f"\nLocal models folder [{default_models_path}]: "
            ).strip()

            if not models_path_input:
                models_path_input = str(default_models_path)

            models_path = Path(models_path_input).expanduser()

            if models_path.exists():
                self.models_path = models_path
                break
            else:
                print(f"❌ Path not found: {models_path}")
                print("Please enter a valid path.")

        # Scan for models
        self.scan_models()

        if self.local_models:
            print(f"\n✅ Found {len(self.local_models)} model folder(s):")
            for i, model in enumerate(self.local_models, 1):
                size_gb = sum(
                    f.stat().st_size for f in model.rglob("*") if f.is_file()
                ) / (1024**3)
                print(f"   {i}. {model.name} (~{size_gb:.1f} GB)")
        else:
            print("⚠️  No local models found in that directory.")

    def scan_models(self):
        """Scan the models folder for available models."""
        if not self.models_path:
            return

        for item in self.models_path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if it looks like a model directory
                if (item / "model.safetensors").exists() or \
                   (item / "model.gguf").exists() or \
                   (item / "config.json").exists() or \
                   (item / "model").is_dir():
                    self.local_models.append(item)

    def configure_models(self):
        """Configure which models to use for agent roles."""
        print("\n⚙️  Model Configuration")
        print("-" * 60)

        # Check what's in Ollama
        print("\nChecking Ollama for available models...")
        try:
            result = subprocess.run(
                ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    ollama_models = [m["name"] for m in data.get("models", [])]
                    if ollama_models:
                        print(f"✅ Ollama has {len(ollama_models)} model(s):")
                        for model in ollama_models:
                            print(f"   • {model}")
                    else:
                        print("⚠️  No models loaded in Ollama yet.")
                except json.JSONDecodeError:
                    print("⚠️  Could not parse Ollama response.")
        except Exception as e:
            print(f"⚠️  Ollama not responding: {e}")
            print("   Make sure Ollama is running on http://127.0.0.1:11434")

        # Ask which model to use as default
        print("\n📦 Selecting models for agent tasks...")
        print("   (Planner, Executor, Verifier roles)")
        print()

        default_model = "nemotron-3-super-120b-a12b"
        model_choice = input(
            f"Model to use [{default_model}]: "
        ).strip()

        if model_choice:
            default_model = model_choice

        self.config["agent_planner_model"] = default_model
        self.config["agent_executor_model"] = default_model
        self.config["agent_verifier_model"] = default_model

        print(f"\n✅ Configuration:")
        print(f"   Planner:  {default_model}")
        print(f"   Executor: {default_model}")
        print(f"   Verifier: {default_model}")

    def update_env(self):
        """Update .env file with configuration."""
        env_file = self.repo_path / ".env"

        if not env_file.exists():
            print("⚠️  .env file not found!")
            return False

        print("\n💾 Updating .env configuration...")

        with open(env_file, "r") as f:
            content = f.read()

        # Replace model configurations
        import re

        content = re.sub(
            r"AGENT_PLANNER_MODEL=.*",
            f"AGENT_PLANNER_MODEL={self.config.get('agent_planner_model', 'gemma4:latest')}",
            content
        )
        content = re.sub(
            r"AGENT_EXECUTOR_MODEL=.*",
            f"AGENT_EXECUTOR_MODEL={self.config.get('agent_executor_model', 'gemma4:latest')}",
            content
        )
        content = re.sub(
            r"AGENT_VERIFIER_MODEL=.*",
            f"AGENT_VERIFIER_MODEL={self.config.get('agent_verifier_model', 'gemma4:latest')}",
            content
        )

        with open(env_file, "w") as f:
            f.write(content)

        print("✅ .env updated")
        return True

    def check_services(self):
        """Check if services are already running."""
        print("\n🔍 Checking services...")

        # Check Ollama
        try:
            result = subprocess.run(
                ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
                capture_output=True,
                timeout=2
            )
            ollama_running = result.returncode == 0
        except:
            ollama_running = False

        # Check proxy
        try:
            result = subprocess.run(
                ["curl", "-s", "http://127.0.0.1:8000/health"],
                capture_output=True,
                timeout=2
            )
            proxy_running = result.returncode == 0
        except:
            proxy_running = False

        print(f"  Ollama:  {'✅ Running' if ollama_running else '⚠️  Not running'}")
        print(f"  Proxy:   {'✅ Running' if proxy_running else '⚠️  Not running'}")

        return ollama_running, proxy_running

    def start_services(self):
        """Start the proxy server."""
        print("\n🚀 Starting proxy server...")

        venv_python = self.repo_path / ".venv/bin/python"

        if not venv_python.exists():
            print("❌ Virtual environment not found!")
            print("   Run: python3 -m venv .venv")
            return False

        # Start in background
        try:
            subprocess.Popen(
                [str(venv_python), "-m", "uvicorn", "proxy:app", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(self.repo_path)
            )

            print("✅ Proxy starting... (takes 5-10 seconds)")

            # Wait for it to be ready
            import time
            for i in range(20):
                try:
                    subprocess.run(
                        ["curl", "-s", "http://127.0.0.1:8000/health"],
                        capture_output=True,
                        timeout=1
                    )
                    print("✅ Proxy is ready!")
                    return True
                except:
                    time.sleep(0.5)

            print("⚠️  Proxy took too long to start. Check logs with: tail -f /tmp/proxy.log")
            return False

        except Exception as e:
            print(f"❌ Error starting proxy: {e}")
            return False

    def summary(self):
        """Show final summary."""
        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)

        print("\n🎯 Next Steps:")
        print()
        print("  1. Check proxy health:")
        print("     curl http://localhost:8000/health")
        print()
        print("  2. Submit a task:")
        print("     python task_runner.py 'Your task here'")
        print()
        print("  3. View the dashboard:")
        print("     http://localhost:8000/admin/ui/")
        print()
        print("  4. Use with Claude Code:")
        print("     ANTHROPIC_BASE_URL=http://localhost:8000 claude code")
        print()
        print("Documentation: See QUICK_START.md")
        print()

    def run(self):
        """Run the full setup."""
        self.welcome()

        try:
            # Check if services are already running
            ollama_ok, proxy_ok = self.check_services()

            if proxy_ok:
                print("\n✅ Proxy is already running!")
                print("   Skipping startup. You're ready to go.")
                self.summary()
                return

            # Find models
            self.find_local_models()

            # Configure
            self.configure_models()

            # Update env
            if not self.update_env():
                print("⚠️  Could not update .env file")

            # Start services
            if not ollama_ok:
                print("\n⚠️  Ollama is not running.")
                if sys.platform == "darwin":
                    print("   Start it: open /Applications/Ollama.app")
                else:
                    print("   Start it: ollama serve")

            if self.start_services():
                self.summary()
            else:
                print("\n⚠️  Setup completed but proxy did not start.")
                print("   Try: .venv/bin/python -m uvicorn proxy:app --port 8000")

        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled.")
            sys.exit(1)


if __name__ == "__main__":
    setup = LocalLLMSetup()
    setup.run()
