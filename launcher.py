#!/usr/bin/env python3
"""
Local LLM Server Launcher - One-button service start with web UI.
Run this once, then access the UI at http://localhost:3000
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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Services management
class ServiceManager:
    def __init__(self):
        self.proxy_process = None
        self.tunnel_process = None
        self.repo_path = Path.cwd()
        self.venv_python = self.repo_path / ".venv/bin/python"
        self.status = {
            "proxy": "stopped",
            "ollama": "checking",
            "tunnel": "stopped",
            "public_url": None,
        }

    def check_proxy(self):
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def check_ollama(self):
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def start_proxy(self):
        """Start the FastAPI proxy server."""
        if self.proxy_process and self.proxy_process.poll() is None:
            self.status["proxy"] = "running"
            return True

        if not self.venv_python.exists():
            self.status["proxy"] = "error"
            return False

        try:
            self.proxy_process = subprocess.Popen(
                [str(self.venv_python), "-m", "uvicorn", "proxy:app", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_path)
            )

            # Wait for it to start
            for _ in range(20):
                if self.check_proxy():
                    self.status["proxy"] = "running"
                    return True
                time.sleep(0.5)

            self.status["proxy"] = "starting"
            return True

        except Exception as e:
            self.status["proxy"] = f"error: {str(e)}"
            return False

    def start_tunnel(self):
        """Start ngrok tunnel."""
        if self.tunnel_process and self.tunnel_process.poll() is None:
            self.status["tunnel"] = "running"
            return True

        auth_token = os.getenv("NGROK_AUTH_TOKEN", "").strip()
        if not auth_token:
            self.status["tunnel"] = "error: no auth token"
            return False

        try:
            # Start ngrok tunnel via pyngrok
            tunnel_script = self.repo_path / "start_tunnel_simple.py"

            self.tunnel_process = subprocess.Popen(
                [str(self.venv_python), str(tunnel_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.repo_path),
                env={**os.environ, "NGROK_AUTH_TOKEN": auth_token}
            )

            self.status["tunnel"] = "starting"

            # Read output to get public URL
            time.sleep(2)
            public_url = os.getenv("NGROK_PUBLIC_URL", "").strip()
            self.status["public_url"] = public_url or "pending-ngrok-url"
            self.status["tunnel"] = "running"

            return True

        except Exception as e:
            self.status["tunnel"] = f"error: {str(e)}"
            return False

    def stop_proxy(self):
        if self.proxy_process:
            self.proxy_process.terminate()
            self.proxy_process = None
            self.status["proxy"] = "stopped"

    def stop_tunnel(self):
        if self.tunnel_process:
            self.tunnel_process.terminate()
            self.tunnel_process = None
            self.status["tunnel"] = "stopped"

    def get_status(self):
        # Update real status
        self.status["proxy"] = "running" if self.check_proxy() else self.status["proxy"]
        self.status["ollama"] = "running" if self.check_ollama() else "not running"

        return self.status


# FastAPI app
app = FastAPI(title="Local LLM Server Launcher")
manager = ServiceManager()


# HTML UI
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local LLM Server Launcher</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 28px;
            color: #333;
            margin-bottom: 8px;
        }

        .header p {
            color: #666;
            font-size: 14px;
        }

        .services {
            display: grid;
            gap: 20px;
            margin-bottom: 30px;
        }

        .service {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }

        .service-status {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-dot.running {
            background: #4caf50;
        }

        .status-dot.stopped {
            background: #f44336;
        }

        .status-dot.checking {
            background: #ff9800;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }

        .service-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .service-name {
            font-weight: 600;
            color: #333;
        }

        .service-details {
            font-size: 12px;
            color: #999;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }

        .btn-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }

        .btn-danger {
            background: #f44336;
            color: white;
            font-size: 12px;
        }

        .btn-danger:hover {
            background: #da190b;
        }

        .quick-start {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
        }

        .quick-start h3 {
            color: #2196f3;
            margin-bottom: 8px;
            font-size: 14px;
        }

        .quick-start button {
            background: #2196f3;
            color: white;
            width: 100%;
            padding: 12px;
            font-size: 16px;
            font-weight: 700;
            margin-top: 10px;
        }

        .quick-start button:hover {
            background: #1976d2;
        }

        .public-url {
            background: #f0f4ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }

        .public-url-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }

        .public-url-value {
            font-size: 14px;
            font-weight: 600;
            color: #667eea;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            user-select: all;
        }

        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }

        .status-item {
            text-align: center;
        }

        .status-label {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .status-value {
            font-size: 13px;
            font-weight: 600;
            color: #333;
        }

        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Local LLM Server</h1>
            <p>One-click service launcher</p>
        </div>

        <div class="quick-start">
            <h3>⚡ Quick Start</h3>
            <button class="btn-primary" onclick="startAll()" style="width: 100%; padding: 12px; font-size: 16px;">
                START ALL SERVICES
            </button>
        </div>

        <div id="publicUrl" class="public-url" style="display: none;">
            <div class="public-url-label">🌐 Public URL</div>
            <div class="public-url-value" id="publicUrlValue">Loading...</div>
        </div>

        <div class="services">
            <div class="service">
                <div class="service-status">
                    <div class="status-dot stopped" id="proxyDot"></div>
                    <div class="service-info">
                        <div class="service-name">Proxy Server</div>
                        <div class="service-details">http://localhost:8000</div>
                    </div>
                </div>
                <div class="action-buttons">
                    <button class="btn-primary" onclick="startProxy()">Start</button>
                    <button class="btn-danger" onclick="stopProxy()">Stop</button>
                </div>
            </div>

            <div class="service">
                <div class="service-status">
                    <div class="status-dot checking" id="ollamaDot"></div>
                    <div class="service-info">
                        <div class="service-name">Ollama</div>
                        <div class="service-details">http://localhost:11434</div>
                    </div>
                </div>
                <div class="action-buttons">
                    <button class="btn-primary" disabled>Started</button>
                </div>
            </div>

            <div class="service">
                <div class="service-status">
                    <div class="status-dot stopped" id="tunnelDot"></div>
                    <div class="service-info">
                        <div class="service-name">ngrok Tunnel</div>
                        <div class="service-details">Public internet access</div>
                    </div>
                </div>
                <div class="action-buttons">
                    <button class="btn-primary" onclick="startTunnel()">Start</button>
                    <button class="btn-danger" onclick="stopTunnel()">Stop</button>
                </div>
            </div>
        </div>

        <div class="status-grid">
            <div class="status-item">
                <div class="status-label">Proxy</div>
                <div class="status-value" id="proxyStatus">Stopped</div>
            </div>
            <div class="status-item">
                <div class="status-label">Ollama</div>
                <div class="status-value" id="ollamaStatus">Checking...</div>
            </div>
        </div>
    </div>

    <script>
        const API_URL = "http://localhost:3000/api";

        async function startAll() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Starting...';

            await startProxy();
            await new Promise(r => setTimeout(r, 2000));
            await startTunnel();

            btn.disabled = false;
            btn.innerHTML = "START ALL SERVICES";
            updateStatus();
        }

        async function startProxy() {
            try {
                const res = await fetch(`${API_URL}/services/proxy/start`, { method: "POST" });
                const data = await res.json();
                updateStatus();
            } catch (e) {
                alert("Error starting proxy: " + e);
            }
        }

        async function stopProxy() {
            try {
                const res = await fetch(`${API_URL}/services/proxy/stop`, { method: "POST" });
                updateStatus();
            } catch (e) {
                alert("Error stopping proxy: " + e);
            }
        }

        async function startTunnel() {
            try {
                const res = await fetch(`${API_URL}/services/tunnel/start`, { method: "POST" });
                const data = await res.json();
                updateStatus();
            } catch (e) {
                alert("Error starting tunnel: " + e);
            }
        }

        async function stopTunnel() {
            try {
                const res = await fetch(`${API_URL}/services/tunnel/stop`, { method: "POST" });
                updateStatus();
            } catch (e) {
                alert("Error stopping tunnel: " + e);
            }
        }

        async function updateStatus() {
            try {
                const res = await fetch(`${API_URL}/status`);
                const status = await res.json();

                // Update proxy
                const proxyDot = document.getElementById("proxyDot");
                const proxyStatus = document.getElementById("proxyStatus");
                proxyDot.className = `status-dot ${status.proxy === "running" ? "running" : "stopped"}`;
                proxyStatus.textContent = status.proxy.charAt(0).toUpperCase() + status.proxy.slice(1);

                // Update ollama
                const ollamaDot = document.getElementById("ollamaDot");
                const ollamaStatus = document.getElementById("ollamaStatus");
                ollamaDot.className = `status-dot ${status.ollama === "running" ? "running" : "checking"}`;
                ollamaStatus.textContent = status.ollama.charAt(0).toUpperCase() + status.ollama.slice(1);

                // Update tunnel
                const tunnelDot = document.getElementById("tunnelDot");
                tunnelDot.className = `status-dot ${status.tunnel === "running" ? "running" : "stopped"}`;

                // Show public URL if tunnel is running
                if (status.tunnel === "running" && status.public_url) {
                    document.getElementById("publicUrl").style.display = "block";
                    document.getElementById("publicUrlValue").textContent = status.public_url;
                }
            } catch (e) {
                console.error("Error updating status:", e);
            }
        }

        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the launcher UI."""
    return HTML_UI


class StatusResponse(BaseModel):
    proxy: str
    ollama: str
    tunnel: str
    public_url: Optional[str]


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get current service status."""
    return manager.get_status()


@app.post("/api/services/proxy/start")
async def start_proxy():
    """Start proxy service."""
    success = manager.start_proxy()
    return {
        "success": success,
        "status": manager.status["proxy"],
        "url": "http://localhost:8000"
    }


@app.post("/api/services/proxy/stop")
async def stop_proxy():
    """Stop proxy service."""
    manager.stop_proxy()
    return {"success": True, "status": "stopped"}


@app.post("/api/services/tunnel/start")
async def start_tunnel():
    """Start ngrok tunnel."""
    success = manager.start_tunnel()
    return {
        "success": success,
        "status": manager.status["tunnel"],
        "public_url": manager.status.get("public_url")
    }


@app.post("/api/services/tunnel/stop")
async def stop_tunnel():
    """Stop ngrok tunnel."""
    manager.stop_tunnel()
    return {"success": True, "status": "stopped"}


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*60)
    print("🚀 Local LLM Server Launcher")
    print("="*60)
    print("\n📱 Opening launcher UI at http://localhost:3000")
    print("   Click 'START ALL SERVICES' to begin\n")

    uvicorn.run(app, host="127.0.0.1", port=3000)
