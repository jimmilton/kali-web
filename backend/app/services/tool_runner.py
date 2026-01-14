"""Local tool runner for executing security tools.

Copyright 2025 milbert.ai

Runs tools directly on the system instead of in Docker containers.
"""

import asyncio
import logging
import os
import signal
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


class ToolRunner:
    """Runs security tools directly on the local system."""

    def __init__(
        self,
        command: str,
        timeout: int = 3600,
        working_dir: Optional[str] = None,
    ):
        self.command = command
        self.timeout = timeout
        self.working_dir = working_dir or str(settings.outputs_path)
        self.process: Optional[asyncio.subprocess.Process] = None

    async def run(
        self,
        output_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Tuple[int, str]:
        """
        Run the tool and stream output.

        Args:
            output_callback: Async callback for output lines (content, type)

        Returns:
            Tuple of (exit_code, process_id)
        """
        # Ensure working directory exists
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Executing: {self.command}")

        try:
            # Create subprocess
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
                env=self._get_env(),
            )

            process_id = str(self.process.pid)

            # Read output streams concurrently
            async def read_stream(stream, output_type: str):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    if output_callback:
                        await output_callback(decoded, output_type)

            # Create tasks for reading stdout and stderr
            stdout_task = asyncio.create_task(read_stream(self.process.stdout, "stdout"))
            stderr_task = asyncio.create_task(read_stream(self.process.stderr, "stderr"))

            try:
                # Wait for process with timeout
                await asyncio.wait_for(
                    asyncio.gather(stdout_task, stderr_task, self.process.wait()),
                    timeout=self.timeout,
                )
                exit_code = self.process.returncode

            except asyncio.TimeoutError:
                logger.warning(f"Process timed out after {self.timeout}s")
                await self.kill()
                raise

            logger.info(f"Process completed with exit code {exit_code}")
            return exit_code, process_id

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            raise

    async def kill(self):
        """Kill the running process."""
        if self.process and self.process.returncode is None:
            try:
                # Try graceful termination first
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Force kill
                    self.process.kill()
                    await self.process.wait()
                logger.info("Process killed")
            except ProcessLookupError:
                pass  # Process already dead

    def _get_env(self) -> dict:
        """Get environment variables for the process."""
        env = os.environ.copy()
        # Add tool-specific paths
        env["PATH"] = f"/usr/local/bin:/usr/bin:/bin:{env.get('PATH', '')}"
        # Disable interactive prompts
        env["DEBIAN_FRONTEND"] = "noninteractive"
        return env


# Tool command templates
TOOL_COMMANDS = {
    "nmap": "nmap {args}",
    "nuclei": "nuclei {args}",
    "subfinder": "subfinder {args}",
    "httpx": "httpx {args}",
    "gobuster": "gobuster {args}",
    "ffuf": "ffuf {args}",
    "nikto": "nikto {args}",
    "masscan": "masscan {args}",
    "sqlmap": "sqlmap {args}",
    "hydra": "hydra {args}",
    "john": "john {args}",
    "whatweb": "whatweb {args}",
    "wpscan": "wpscan {args}",
    "sslscan": "sslscan {args}",
    "dirb": "dirb {args}",
    "wfuzz": "wfuzz {args}",
}


def get_tool_command(tool_slug: str, args: str) -> Optional[str]:
    """Get the command for a tool."""
    template = TOOL_COMMANDS.get(tool_slug)
    if template:
        return template.format(args=args)
    return None


def is_tool_installed(tool_name: str) -> bool:
    """Check if a tool is installed on the system."""
    return shutil.which(tool_name) is not None


def get_installed_tools() -> list:
    """Get list of installed tools."""
    installed = []
    for tool in TOOL_COMMANDS.keys():
        if is_tool_installed(tool):
            installed.append(tool)
    return installed
