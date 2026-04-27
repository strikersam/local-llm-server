#!/usr/bin/env python3
"""
Local Service Daemon - Controls services and communicates with GitHub Pages UI.
Runs on user's machine and listens for commands from the web UI.
"""

import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# === Data Models ===
class ServiceConfig(BaseModel):
    """Configuration for services."""
    repo_path: str
    models_path: str
    proxy_port: int = 8000
    ollama_base: str = "http://127.0.0.1:11434"


class ServiceStatus(BaseModel):
    """Status of all services."""
    proxy: str  # running, stopped, error
    ollama: str  # running, not_running
    tunnel: str  # running, stopped
    public_url: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


# === Service Manager ===
class ServiceDaemon:
    def __init__(self):
        self.repo_path: Optional[Path] = None
        self.models_path: Optional[Path] = None
        self.proxy_process: Optional[subprocess.Popen] = None
        self.tunnel_process: Optional[subprocess.Popen] = None
        self.venv_python: Optional[Path] = None
        self.config_file = Path.home() / ".local-llm-server" / "config.json"
        self.load_config()

    def load_config(self):
        """Load saved configuration."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                config = json.load(f)
                self.repo_path = Path(config.get("repo_path"))
                self.models_path = Path(config.get("models_path"))
                self.venv_python = self.repo_path / ".venv/bin/python"

    def save_config(self, repo_path: str, models_path: str):
        """Save configuration."""
        self.repo_path = Path(repo_path).expanduser()
        self.models_path = Path(models_path).expanduser()
        self.venv_python = self.repo_path / ".venv/bin/python"

        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w") as f:
            json.dump({
                "repo_path": str(self.repo_path),
                "models_path": str(self.models_path),
                "configured_at": datetime.now().isoformat()
            }, f, indent=2)

    def validate_paths(self) -> tuple[bool, str]:
        """Validate configured paths."""
        if not self.repo_path or not self.models_path:
            return False, "Paths not configured"

        if not self.repo_path.exists():
            return False, f"Repo path not found: {self.repo_path}"

        if not self.models_path.exists():
            return False, f"Models path not found: {self.models_path}"

        if not self.venv_python or not self.venv_python.exists():
            return False, f"Virtual environment not found: {self.venv_python}"

        return True, "OK"

    def check_proxy(self) -> bool:
        """Check if proxy is running."""
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def start_proxy(self) -> tuple[bool, str]:
        """Start the proxy server."""
        if self.proxy_process and self.proxy_process.poll() is None:
            if self.check_proxy():
                return True, "Proxy already running"

        valid, msg = self.validate_paths()
        if not valid:
            return False, msg

        try:
            self.proxy_process = subprocess.Popen(
                [str(self.venv_python), "-m", "uvicorn", "proxy:app", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(self.repo_path)
            )

            # Wait for startup
            for _ in range(30):
                if self.check_proxy():
                    return True, "Proxy started successfully"
                time.sleep(0.5)

            return True, "Proxy starting (may take a moment)"

        except Exception as e:
            return False, f"Failed to start proxy: {str(e)}"

    def stop_proxy(self) -> tuple[bool, str]:
        """Stop the proxy server."""
        if self.proxy_process:
            try:
                self.proxy_process.terminate()
                self.proxy_process.wait(timeout=5)
            except:
                self.proxy_process.kill()
            self.proxy_process = None

        return True, "Proxy stopped"

    def start_tunnel(self) -> tuple[bool, str]:
        """Start ngrok tunnel."""
        if self.tunnel_process and self.tunnel_process.poll() is None:
            return True, "Tunnel already running"

        auth_token = os.getenv("NGROK_AUTH_TOKEN", "").strip()
        if not auth_token:
            return False, "NGROK_AUTH_TOKEN not set in .env"

        valid, msg = self.validate_paths()
        if not valid:
            return False, msg

        try:
            tunnel_script = self.repo_path / "start_tunnel_simple.py"

            self.tunnel_process = subprocess.Popen(
                [str(self.venv_python), str(tunnel_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_path),
                env={**os.environ, "NGROK_AUTH_TOKEN": auth_token}
            )

            time.sleep(2)
            return True, "Tunnel starting"

        except Exception as e:
            return False, f"Failed to start tunnel: {str(e)}"

    def stop_tunnel(self) -> tuple[bool, str]:
        """Stop ngrok tunnel."""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
            except:
                self.tunnel_process.kill()
            self.tunnel_process = None

        return True, "Tunnel stopped"

    def get_status(self) -> ServiceStatus:
        """Get current status of all services."""
        proxy_status = "running" if self.check_proxy() else "stopped"
        ollama_status = "running" if self.check_ollama() else "not_running"
        tunnel_status = "running" if (self.tunnel_process and self.tunnel_process.poll() is None) else "stopped"
        public_url = os.getenv("NGROK_PUBLIC_URL")

        return ServiceStatus(
            proxy=proxy_status,
            ollama=ollama_status,
            tunnel=tunnel_status,
            public_url=public_url,
            timestamp=datetime.now().isoformat()
        )


# === FastAPI App ===
app = FastAPI(title="Local LLM Server Daemon")
daemon = ServiceDaemon()

# Enable CORS for GitHub Pages origin and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://strikersam.github.io",
        "http://localhost:3001",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "*"  # Allow all origins for localhost development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "version": "1.0"}


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the setup wizard UI."""
    setup_html_path = Path(__file__).parent / "github-pages-setup.html"
    if setup_html_path.exists():
        with open(setup_html_path) as f:
            return f.read()
    return "<h1>Setup wizard not found. Place github-pages-setup.html in the repo root.</h1>"


@app.post("/api/configure")
async def configure(config: ServiceConfig):
    """Configure paths and services."""
    try:
        daemon.save_config(config.repo_path, config.models_path)
        valid, msg = daemon.validate_paths()

        if valid:
            return {
                "success": True,
                "message": "Configuration saved",
                "repo_path": str(daemon.repo_path),
                "models_path": str(daemon.models_path)
            }
        else:
            return {
                "success": False,
                "message": msg
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.get("/api/status")
async def get_status():
    """Get current service status."""
    status = daemon.get_status()
    return status.dict()


@app.post("/api/services/proxy/start")
async def start_proxy():
    """Start proxy service."""
    success, msg = daemon.start_proxy()
    status = daemon.get_status()
    return {
        "success": success,
        "message": msg,
        "status": status.dict()
    }


@app.post("/api/services/proxy/stop")
async def stop_proxy():
    """Stop proxy service."""
    success, msg = daemon.stop_proxy()
    status = daemon.get_status()
    return {
        "success": success,
        "message": msg,
        "status": status.dict()
    }


@app.post("/api/services/tunnel/start")
async def start_tunnel():
    """Start ngrok tunnel."""
    success, msg = daemon.start_tunnel()
    status = daemon.get_status()
    return {
        "success": success,
        "message": msg,
        "status": status.dict()
    }


@app.post("/api/services/tunnel/stop")
async def stop_tunnel():
    """Stop ngrok tunnel."""
    success, msg = daemon.stop_tunnel()
    status = daemon.get_status()
    return {
        "success": success,
        "message": msg,
        "status": status.dict()
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 Local LLM Server Service Daemon")
    print("="*70)
    print("\n📱 Daemon listening on http://localhost:3001")
    print("   GitHub Pages UI can now control your services")
    print("   https://strikersam.github.io/local-llm-server/\n")

    uvicorn.run(app, host="127.0.0.1", port=3001, log_level="warning")
