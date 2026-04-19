from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


def _creationflags() -> int:
    return getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


@dataclass(frozen=True)
class ServiceState:
    name: str
    running: bool
    pid: int | None
    detail: str | None = None


class WindowsServiceManager:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.logs_dir = root / "logs"
        self.pid_file = root / "server.pids"
        self.proxy_port = int(os.environ.get("PROXY_PORT", "8000"))
        self.ollama_port = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").split(":")[-1]

    def _run_ps(self, script: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=check,
        )

    def _spawn_file(self, filename: str) -> None:
        if sys.platform != "win32":
            raise ValueError(
                f"Cannot start '{filename}' — batch files are Windows-only. "
                "Restart the proxy manually: uvicorn proxy:app --reload --port 8000"
            )
        subprocess.Popen(
            ["cmd.exe", "/c", str(self.root / filename)],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_creationflags(),
        )

    def _spawn_tunnel(self) -> None:
        cf_exe = os.environ.get("CLOUDFLARED_EXE")
        if cf_exe and Path(cf_exe).exists():
            # Cloudflare tunnel: cloudflared tunnel --url http://localhost:PORT
            args = [cf_exe, "tunnel", "--url", f"http://localhost:{self.proxy_port}"]
        else:
            ngrok_exe = os.environ.get("NGROK_EXE")
            if not ngrok_exe:
                candidate = Path.home() / "AppData" / "Local" / "ngrok" / "ngrok.exe"
                ngrok_exe = str(candidate) if candidate.exists() else "ngrok"
            args = [ngrok_exe, "http", str(self.proxy_port), "--log=stderr"]
            domain = os.environ.get("NGROK_DOMAIN", "").strip()
            if domain:
                args.append(f"--url={domain}")

        subprocess.Popen(
            args,
            cwd=self.root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_creationflags(),
        )

    def _spawn_cmd(self, command: str) -> None:
        if sys.platform != "win32":
            raise ValueError(
                "PowerShell commands are Windows-only. "
                "Restart the proxy manually: uvicorn proxy:app --reload --port 8000"
            )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_creationflags(),
        )

    def _spawn_unix(self) -> None:
        """Spawn a new proxy process on Linux/Mac using the current Python interpreter."""
        port = str(self.proxy_port)
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "proxy:app", "--port", port],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def _read_pid_map(self) -> dict[str, int]:
        if not self.pid_file.is_file():
            return {}
        try:
            raw = json.loads(self.pid_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
        out: dict[str, int] = {}
        for key, value in raw.items():
            if isinstance(value, int):
                out[key] = value
        return out

    def _write_pid_map(self, pid_map: dict[str, int]) -> None:
        payload = {
            "ollama": pid_map.get("ollama"),
            "proxy": pid_map.get("proxy"),
            "tunnel": pid_map.get("tunnel"),
        }
        self.pid_file.write_text(json.dumps(payload), encoding="utf-8")

    def _find_pid(self, service: str) -> int | None:
        if sys.platform != "win32":
            return None
        scripts = {
            "proxy": "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*proxy:app*' } | Select-Object -ExpandProperty ProcessId -First 1",
            "tunnel": "Get-Process -Name ngrok, cloudflared -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id -First 1",
            "ollama": "Get-Process -Name ollama -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id -First 1",
        }
        completed = self._run_ps(scripts[service])
        value = (completed.stdout or "").strip()
        return int(value) if value.isdigit() else None

    def _state(self, service: str) -> ServiceState:
        pid = self._find_pid(service)
        detail = None
        if service == "proxy":
            detail = f"http://localhost:{self.proxy_port}/health"
        elif service == "ollama":
            detail = f"http://localhost:{self.ollama_port}/api/tags"
        elif service == "tunnel":
            detail = self.get_tunnel_url()
        return ServiceState(name=service, running=pid is not None, pid=pid, detail=detail)

    def get_tunnel_url(self) -> str | None:
        # A manually configured PUBLIC_URL always wins (permanent/named tunnel).
        configured = os.environ.get("PUBLIC_URL", "").strip()
        if configured:
            return configured
        # Query ngrok's local API for the live tunnel URL.
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=2) as resp:
                data = json.loads(resp.read())
            for t in data.get("tunnels", []):
                url = t.get("public_url", "")
                if url.startswith("https://"):
                    return url
        except Exception:
            pass
        return None

    def get_status(self) -> dict[str, object]:
        services = {
            "ollama": asdict(self._state("ollama")),
            "proxy": asdict(self._state("proxy")),
            "tunnel": asdict(self._state("tunnel")),
        }
        return {
            "services": services,
            "public_url": self.get_tunnel_url(),
            "pid_file_present": self.pid_file.is_file(),
            "timestamp": int(time.time()),
        }

    def start(self, target: str) -> dict[str, object]:
        pid_map = self._read_pid_map()
        if target == "stack":
            if not self._find_pid("ollama"):
                self._spawn_file("run_ollama.bat")
                time.sleep(1)
                pid = self._find_pid("ollama")
                if pid:
                    pid_map["ollama"] = pid
            if not self._find_pid("proxy"):
                self._spawn_file("run_proxy.bat")
                time.sleep(1)
                pid = self._find_pid("proxy")
                if pid:
                    pid_map["proxy"] = pid
            if not self._find_pid("tunnel"):
                self._spawn_tunnel()
                time.sleep(1)
                pid = self._find_pid("tunnel")
                if pid:
                    pid_map["tunnel"] = pid
            self._write_pid_map(pid_map)
            return {"ok": True, "message": "Start requested for stack", "status": self.get_status()}

        if target == "ollama" and not self._find_pid("ollama"):
            self._spawn_file("run_ollama.bat")
            time.sleep(1)
            pid = self._find_pid("ollama")
            if pid:
                pid_map["ollama"] = pid
        elif target == "proxy" and not self._find_pid("proxy"):
            if sys.platform == "win32":
                self._spawn_file("run_proxy.bat")
            else:
                self._spawn_unix()
            time.sleep(1)
            pid = self._find_pid("proxy")
            if pid:
                pid_map["proxy"] = pid
        elif target == "tunnel" and not self._find_pid("tunnel"):
            self._spawn_tunnel()
            time.sleep(1)
            pid = self._find_pid("tunnel")
            if pid:
                pid_map["tunnel"] = pid
        self._write_pid_map(pid_map)
        return {"ok": True, "message": f"Start requested for {target}", "status": self.get_status()}

    def stop(self, target: str, current_proxy_pid: int | None = None) -> dict[str, object]:
        if target == "stack":
            self._spawn_cmd(f"Start-Sleep -Seconds 1; & '{self.root / 'stop_server.ps1'}'")
            return {
                "ok": True,
                "message": "Stop requested for stack. The admin connection will drop once the proxy stops.",
            }

        pid = self._find_pid(target)
        if not pid:
            return {"ok": True, "message": f"{target} was already stopped", "status": self.get_status()}

        if target == "proxy" and current_proxy_pid and pid == current_proxy_pid:
            self._spawn_cmd(f"Start-Sleep -Seconds 1; Stop-Process -Id {pid} -Force")
            return {
                "ok": True,
                "message": "Proxy stop requested. This session will disconnect once the response completes.",
            }

        self._run_ps(f"Stop-Process -Id {pid} -Force", check=False)
        return {"ok": True, "message": f"Stopped {target}", "status": self.get_status()}

    def control(self, action: str, target: str, current_proxy_pid: int | None = None) -> dict[str, object]:
        if action == "restart" and target == "stack":
            self._spawn_cmd(
                f"Start-Sleep -Seconds 1; & '{self.root / 'stop_server.ps1'}'; "
                f"Start-Sleep -Seconds 2; & '{self.root / 'start_server.ps1'}'"
            )
            return {
                "ok": True,
                "message": "Restart requested for stack. The admin connection will drop while the proxy restarts.",
            }
        if action == "restart" and target == "proxy" and current_proxy_pid:
            if sys.platform == "win32":
                self._spawn_cmd(
                    f"Start-Sleep -Seconds 1; Stop-Process -Id {current_proxy_pid} -Force; "
                    f"Start-Sleep -Seconds 2; cmd.exe /c '{self.root / 'run_proxy.bat'}'"
                )
            else:
                self._spawn_unix()
                import threading
                def _kill_after() -> None:
                    time.sleep(1)
                    try:
                        os.kill(current_proxy_pid, 15)  # SIGTERM
                    except OSError:
                        pass
                threading.Thread(target=_kill_after, daemon=True).start()
            return {
                "ok": True,
                "message": "Proxy restart requested. The admin connection will drop briefly.",
            }
        if action == "start":
            return self.start(target)
        if action == "stop":
            return self.stop(target, current_proxy_pid=current_proxy_pid)
        if action == "restart":
            self.stop(target, current_proxy_pid=current_proxy_pid)
            time.sleep(1)
            return self.start(target)
        raise ValueError(f"Unsupported action: {action}")
