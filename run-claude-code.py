#!/usr/bin/env python3
"""
Cross-platform Claude Code launcher for local models.

Auto-detects OS and runs the appropriate script with full error handling.
Now includes automatic Ollama startup and setup detection!

Works on Windows, Linux, and macOS.

Usage:
    python run-claude-code.py                    # Auto-detect everything and launch!
    python run-claude-code.py --local             # Use localhost (default)
    python run-claude-code.py --interactive       # Prompt for setup
    python run-claude-code.py --model deepseek    # Use specific model
    python run-claude-code.py --setup             # Run setup only
    python run-claude-code.py --stop              # Stop proxy
"""

import os
import sys
import platform
import subprocess
import argparse
import socket
import time
from pathlib import Path


class OllamaManager:
    """Manage Ollama service startup and health checks."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.host = "localhost"
        self.port = 11434
    
    def is_running(self) -> bool:
        """Check if Ollama is running."""
        try:
            sock = socket.create_connection((self.host, self.port), timeout=2)
            sock.close()
            return True
        except (socket.timeout, socket.error, ConnectionRefusedError):
            return False
    
    def start_ollama(self) -> bool:
        """Attempt to start Ollama service."""
        print("[INFO] Starting Ollama service...")
        
        os_name = platform.system().lower()
        
        try:
            if os_name == "windows":
                # Try to find Ollama executable
                possible_paths = [
                    Path("C:\\Users") / os.getenv("USERNAME", "user") / "AppData\\Roaming\\aipc\\runtime\\ollama\\ollama.exe",
                    Path("C:\\Program Files\\Ollama\\ollama.exe"),
                    Path.home() / "AppData\\Roaming\\Ollama\\ollama.exe",
                ]
                
                for ollama_path in possible_paths:
                    if ollama_path.exists():
                        subprocess.Popen(
                            str(ollama_path),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        print(f"[OK] Ollama started from {ollama_path}")
                        # Wait for startup
                        for i in range(10):
                            time.sleep(1)
                            if self.is_running():
                                print("[OK] Ollama is ready!")
                                return True
                        return True
                
                print("[WARNING] Could not find Ollama executable")
                return False
            else:
                # Try to start Ollama on Unix
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print("[OK] Ollama service started")
                # Wait for startup
                for i in range(10):
                    time.sleep(1)
                    if self.is_running():
                        print("[OK] Ollama is ready!")
                        return True
                return True
        except Exception as e:
            print(f"[WARNING] Could not auto-start Ollama: {e}")
            return False
    
    def ensure_running(self) -> bool:
        """Ensure Ollama is running, start if needed."""
        if self.is_running():
            print("[OK] Ollama is running on port 11434")
            return True
        
        print("[WARNING] Ollama is not running")
        print("[INFO] Attempting to auto-start Ollama...")
        
        return self.start_ollama()


class OsDetector:
    """Detect operating system and available interpreters."""
    
    @staticmethod
    def get_os() -> str:
        """Return normalized OS name."""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    @staticmethod
    def get_interpreter() -> str:
        """Detect PowerShell (Windows) or Bash (Unix)."""
        os_name = OsDetector.get_os()
        
        if os_name == "windows":
            # Try PowerShell
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "exit 0"],
                    capture_output=True,
                    timeout=2,
                )
                return "powershell"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return "cmd"
        else:
            # Bash on Unix
            return "bash"
    
    @staticmethod
    def print_info(msg: str, color: str = "cyan") -> None:
        """Print colored message."""
        colors = {
            "cyan": "\033[0;36m",
            "green": "\033[0;32m",
            "yellow": "\033[1;33m",
            "red": "\033[0;31m",
            "reset": "\033[0m",
        }
        if os_name := OsDetector.get_os() == "windows":
            # No color on Windows cmd
            print(msg)
        else:
            print(f"{colors.get(color, '')}{msg}{colors['reset']}")


class SetupChecker:
    """Check if setup is needed and validate environment."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
    
    def check_env_file(self) -> bool:
        """Check if .env file exists."""
        return (self.repo_root / ".env").exists()
    
    def check_keys_file(self) -> bool:
        """Check if keys.json file exists."""
        return (self.repo_root / "keys.json").exists()
    
    def check_requirements_installed(self) -> bool:
        """Check if required Python packages are installed."""
        try:
            import fastapi
            import uvicorn
            return True
        except ImportError:
            return False
    
    def what_needs_setup(self) -> list:
        """Return list of missing setup items."""
        missing = []
        
        if not self.check_env_file():
            missing.append(".env configuration file")
        
        if not self.check_keys_file():
            missing.append("keys.json API key storage")
        
        if not self.check_requirements_installed():
            missing.append("Python dependencies (fastapi, uvicorn, etc.)")
        
        return missing
    
    def needs_setup(self) -> bool:
        """Return True if any setup is needed."""
        return len(self.what_needs_setup()) > 0
    
    def print_summary(self) -> None:
        """Print what needs setup."""
        missing = self.what_needs_setup()
        if missing:
            print("\n[INFO] The following setup items are missing:")
            for item in missing:
                print(f"  - {item}")
        else:
            print("\n[OK] All setup items are in place!")


class ScriptRunner:
    """Execute platform-specific scripts with error handling."""
    
    def __init__(self):
        self.repo_root = Path(__file__).resolve().parent
        self.os_name = OsDetector.get_os()
        self.interpreter = OsDetector.get_interpreter()
        self.setup_checker = SetupChecker(self.repo_root)
        self.ollama_manager = OllamaManager()
    
    def _build_args(
        self,
        local: bool = False,
        interactive: bool = False,
        model: str = None,
    ) -> list:
        """Build script arguments."""
        args = []
        if local:
            args.append("-Local" if self.os_name == "windows" else "--local")
        if interactive:
            args.append(
                "-Interactive" if self.os_name == "windows" else "--interactive"
            )
        if model:
            args.append(
                f"-Model {model}" if self.os_name == "windows" else f"--model {model}"
            )
        return args
    
    def setup(self) -> int:
        """Run one-time setup."""
        print("\n" + "=" * 70)
        print(f"🔧 Running setup for {self.os_name.upper()}...")
        print("=" * 70 + "\n")
        
        if self.os_name == "windows":
            script = self.repo_root / "setup-claude-code.ps1"
            if not script.exists():
                print(f"❌ Setup script not found: {script}")
                return 1
            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script),
                    ],
                    check=False,
                )
                return result.returncode
            except FileNotFoundError:
                print("❌ PowerShell not found. Trying cmd.exe...")
                return 1
        else:
            script = self.repo_root / "setup-claude-code.sh"
            if not script.exists():
                print(f"❌ Setup script not found: {script}")
                return 1
            try:
                result = subprocess.run(
                    ["bash", str(script)],
                    check=False,
                )
                return result.returncode
            except FileNotFoundError:
                print("❌ Bash not found.")
                return 1
    
    def launch(
        self,
        local: bool = True,
        interactive: bool = False,
        model: str = None,
        auto_setup: bool = True,
    ) -> int:
        """Launch Claude Code, auto-running setup if needed."""
        # Auto-check if setup is needed
        if auto_setup and self.setup_checker.needs_setup():
            print("\n" + "=" * 70)
            print("[INFO] Running required setup first...")
            print("=" * 70)
            self.setup_checker.print_summary()
            print()
            
            setup_result = self.setup()
            if setup_result != 0:
                print("\n[ERROR] Setup failed. Cannot continue.")
                return setup_result
            
            print("\n[OK] Setup completed successfully!")
        
        # Ensure Ollama is running
        print("\n" + "=" * 70)
        print("[INFO] Checking Ollama service...")
        print("=" * 70)
        
        if not self.ollama_manager.ensure_running():
            print("\n[WARNING] Ollama may not be available.")
            print("[INFO] Please ensure Ollama is running before using Claude Code.")
            print("[INFO] You can start Ollama manually or try again.")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                return 1
        
        print("\n" + "=" * 70)
        print(f"🚀 Launching Claude Code ({self.os_name.upper()})...")
        print("=" * 70 + "\n")
        
        if self.os_name == "windows":
            script = self.repo_root / "launch-claude-code.ps1"
            args = self._build_args(local, interactive, model)
            
            if not script.exists():
                print(f"❌ Launch script not found: {script}")
                return 1
            
            try:
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ] + args
                result = subprocess.run(cmd, check=False)
                return result.returncode
            except FileNotFoundError:
                print("❌ PowerShell not found.")
                return 1
        else:
            script = self.repo_root / "launch-claude-code.sh"
            args = self._build_args(local, interactive, model)
            
            if not script.exists():
                print(f"❌ Launch script not found: {script}")
                return 1
            
            try:
                cmd = ["bash", str(script)] + args
                result = subprocess.run(cmd, check=False)
                return result.returncode
            except FileNotFoundError:
                print("❌ Bash not found.")
                return 1
    
    def stop(self, kill_ollama: bool = False) -> int:
        """Stop the proxy."""
        print("\n" + "=" * 70)
        print(f"🛑 Stopping proxy ({self.os_name.upper()})...")
        print("=" * 70 + "\n")
        
        if self.os_name == "windows":
            script = self.repo_root / "stop-proxy.ps1"
            args = ["-KillOllama"] if kill_ollama else []
            
            if not script.exists():
                print(f"❌ Stop script not found: {script}")
                return 1
            
            try:
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ] + args
                result = subprocess.run(cmd, check=False)
                return result.returncode
            except FileNotFoundError:
                print("❌ PowerShell not found.")
                return 1
        else:
            script = self.repo_root / "stop-proxy.sh"
            args = ["--kill-ollama"] if kill_ollama else []
            
            if not script.exists():
                print(f"❌ Stop script not found: {script}")
                return 1
            
            try:
                cmd = ["bash", str(script)] + args
                result = subprocess.run(cmd, check=False)
                return result.returncode
            except FileNotFoundError:
                print("❌ Bash not found.")
                return 1
    
    def show_status(self) -> None:
        """Show system information and setup status."""
        print("\n" + "=" * 70)
        print("📊 System Information")
        print("=" * 70)
        print(f"  OS:          {self.os_name.upper()}")
        print(f"  Platform:    {platform.platform()}")
        print(f"  Python:      {sys.version.split()[0]}")
        print(f"  Interpreter: {self.interpreter}")
        print(f"  Repo:        {self.repo_root}")
        print()
        print("Setup Status:")
        print("=" * 70)
        
        if self.setup_checker.needs_setup():
            print("  [!] Setup needed:")
            self.setup_checker.print_summary()
            print("\n  Run: python run-claude-code.py --setup")
        else:
            print("  [OK] All setup items are in place!")
        
        print("=" * 70 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-platform Claude Code launcher for local models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run-claude-code.py                 # Launch Claude Code (auto-detected)
  python run-claude-code.py --local         # Use local proxy
  python run-claude-code.py --setup         # Setup only
  python run-claude-code.py --stop          # Stop proxy
  python run-claude-code.py --interactive   # Interactive setup
  python run-claude-code.py --model deepseek  # Use specific model
        """,
    )
    
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local proxy (localhost:8000)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run setup only, don't launch Claude Code",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop the proxy",
    )
    parser.add_argument(
        "--kill-ollama",
        action="store_true",
        help="Kill Ollama when stopping",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive setup (prompt for email/dept)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model to use (e.g., claude-sonnet-4-6 or deepseek-r1:32b)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system information",
    )
    
    args = parser.parse_args()
    
    runner = ScriptRunner()
    
    # Show status if requested
    if args.status:
        runner.show_status()
        return 0
    
    # Stop proxy if requested
    if args.stop:
        return runner.stop(kill_ollama=args.kill_ollama)
    
    # Run setup if requested or if it's the first run
    if args.setup:
        return runner.setup()
    
    # Default: Launch Claude Code (with auto-setup if needed)
    try:
        # Set local to True by default
        local = args.local or True
        return runner.launch(
            local=local,
            interactive=args.interactive,
            model=args.model,
            auto_setup=True,  # Auto-run setup if needed
        )
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
