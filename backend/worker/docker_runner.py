"""Docker container runner for tool execution.

Copyright 2025 milbert.ai
"""

import asyncio
import logging
from typing import Callable, Optional, Tuple

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from app.config import settings

logger = logging.getLogger(__name__)


class DockerRunner:
    """Docker container runner for executing security tools."""

    def __init__(
        self,
        image: str,
        command: str,
        timeout: int = 3600,
        memory_limit: str = "2g",
        cpu_limit: float = 2.0,
        network_mode: str = "bridge",
        environment: Optional[dict] = None,
        volumes: Optional[dict] = None,
    ):
        self.image = image
        self.command = command
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.network_mode = network_mode
        self.environment = environment or {}
        self.volumes = volumes or {}

        self.client = docker.from_env()
        self.container = None

    async def run(
        self,
        output_callback: Optional[Callable] = None,
    ) -> Tuple[int, str]:
        """
        Run the tool in a Docker container.

        Args:
            output_callback: Async callback function for streaming output

        Returns:
            Tuple of (exit_code, container_id)
        """
        container_id = None

        try:
            # Pull image if not available
            try:
                self.client.images.get(self.image)
            except ImageNotFound:
                logger.info(f"Pulling image {self.image}...")
                self.client.images.pull(self.image)

            # Prepare container configuration
            container_config = {
                "image": self.image,
                "command": self.command,
                "detach": True,
                "remove": False,  # We'll remove after getting output
                "mem_limit": self.memory_limit,
                "nano_cpus": int(self.cpu_limit * 1e9),
                "network_mode": self.network_mode,
                "environment": self.environment,
                "volumes": self.volumes,
                "security_opt": ["no-new-privileges"],
                "cap_drop": ["ALL"],
                "read_only": False,  # Some tools need to write temp files
            }

            # Add necessary capabilities for network tools
            if self.image.startswith("kali-"):
                container_config["cap_add"] = ["NET_RAW", "NET_ADMIN"]

            logger.info(f"Creating container with image {self.image}")
            self.container = self.client.containers.run(**container_config)
            container_id = self.container.id

            logger.info(f"Container {container_id} started")

            # Stream output with timeout
            exit_code = await self._stream_output(output_callback)

            return exit_code, container_id

        except ContainerError as e:
            logger.error(f"Container error: {e}")
            if output_callback:
                await output_callback(str(e), "stderr")
            return e.exit_status, container_id

        except ImageNotFound as e:
            logger.error(f"Image not found: {e}")
            raise

        except APIError as e:
            logger.error(f"Docker API error: {e}")
            raise

        finally:
            # Cleanup container
            if self.container:
                try:
                    self.container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

    async def _stream_output(
        self,
        output_callback: Optional[Callable],
    ) -> int:
        """Stream container output with timeout."""
        loop = asyncio.get_event_loop()
        buffer = {"stdout": "", "stderr": ""}

        async def read_logs():
            """Read logs in a separate task."""
            try:
                for line in self.container.logs(stream=True, follow=True):
                    decoded = line.decode("utf-8", errors="replace")

                    if output_callback:
                        await output_callback(decoded, "stdout")
                    else:
                        buffer["stdout"] += decoded

            except Exception as e:
                logger.error(f"Error reading logs: {e}")

        # Start log reading task
        log_task = asyncio.create_task(read_logs())

        try:
            # Wait for container to finish with timeout
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self.container.wait),
                timeout=self.timeout,
            )

            # Give a moment for remaining logs to be read
            await asyncio.sleep(0.5)
            log_task.cancel()

            return result["StatusCode"]

        except asyncio.TimeoutError:
            logger.warning(f"Container timeout after {self.timeout}s")
            log_task.cancel()

            # Kill the container
            try:
                self.container.kill()
            except Exception:
                pass

            raise

    def stop(self):
        """Stop the running container."""
        if self.container:
            try:
                self.container.kill()
            except Exception as e:
                logger.warning(f"Failed to kill container: {e}")

    def send_input(self, data: str):
        """Send input to the container's stdin (for interactive tools)."""
        if self.container:
            try:
                # This requires the container to be run with stdin_open=True
                socket = self.container.attach_socket(
                    params={"stdin": True, "stream": True}
                )
                socket._sock.send(data.encode())
            except Exception as e:
                logger.error(f"Failed to send input: {e}")


class DockerManager:
    """Manager for Docker operations."""

    def __init__(self):
        self.client = docker.from_env()

    def list_tool_images(self) -> list:
        """List available tool images."""
        images = self.client.images.list(filters={"reference": "kali-*"})
        return [
            {
                "id": img.id,
                "tags": img.tags,
                "created": img.attrs["Created"],
                "size": img.attrs["Size"],
            }
            for img in images
        ]

    def pull_tool_image(self, image: str) -> bool:
        """Pull a tool image."""
        try:
            self.client.images.pull(image)
            return True
        except Exception as e:
            logger.error(f"Failed to pull image {image}: {e}")
            return False

    def build_tool_image(
        self,
        path: str,
        tag: str,
        buildargs: Optional[dict] = None,
    ) -> bool:
        """Build a tool image from Dockerfile."""
        try:
            self.client.images.build(
                path=path,
                tag=tag,
                buildargs=buildargs or {},
                rm=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to build image {tag}: {e}")
            return False

    def get_running_containers(self) -> list:
        """Get list of running tool containers."""
        containers = self.client.containers.list(
            filters={"ancestor": "kali-*"}
        )
        return [
            {
                "id": c.id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.id,
                "status": c.status,
                "created": c.attrs["Created"],
            }
            for c in containers
        ]

    def cleanup_stopped_containers(self) -> int:
        """Remove stopped tool containers."""
        containers = self.client.containers.list(
            all=True,
            filters={"status": "exited", "ancestor": "kali-*"},
        )
        count = 0
        for container in containers:
            try:
                container.remove()
                count += 1
            except Exception:
                pass
        return count
