"""Docker Engine client wrapper for DockDash.

Provides a clean async-friendly interface to the Docker SDK,
with error handling and connection management.
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Any, Optional

import docker
from docker.errors import (
    APIError,
    ContainerError,
    DockerException,
    ImageNotFound,
    NotFound,
)


class DockerClientError(Exception):
    """Raised when a Docker operation fails."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original


def _handle_errors(func):
    """Decorator to catch Docker SDK exceptions and wrap them."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFound as e:
            raise DockerClientError(f"Resource not found: {e.explanation}", e)
        except ImageNotFound as e:
            raise DockerClientError(f"Image not found: {e.explanation}", e)
        except APIError as e:
            raise DockerClientError(f"Docker API error: {e.explanation}", e)
        except ContainerError as e:
            raise DockerClientError(f"Container error: {e}", e)
        except DockerException as e:
            raise DockerClientError(f"Docker error: {e}", e)

    return wrapper


class DockerClient:
    """Singleton wrapper around the Docker SDK client."""

    _instance: DockerClient | None = None
    _client: docker.DockerClient | None = None

    def __new__(cls) -> DockerClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> bool:
        """Attempt to connect to the Docker daemon. Returns True if successful."""
        try:
            self._client = docker.from_env()
            self._client.ping()
            return True
        except DockerException:
            self._client = None
            return False

    @property
    def connected(self) -> bool:
        """Check if the client is connected to Docker."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    @property
    def client(self) -> docker.DockerClient:
        """Get the underlying Docker client, raising if not connected."""
        if self._client is None:
            raise DockerClientError("Not connected to Docker daemon")
        return self._client

    # ── Async helper ──────────────────────────────────────────────────

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous Docker SDK call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ── Container Operations ──────────────────────────────────────────

    @_handle_errors
    async def list_containers(self, all: bool = True) -> list[dict]:
        """List all containers with their attributes."""
        containers = await self._run_sync(self.client.containers.list, all=all)
        result = []
        for c in containers:
            ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            port_list = []
            for container_port, bindings in ports.items():
                if bindings:
                    for b in bindings:
                        port_list.append(f"{b.get('HostPort', '?')}->{container_port}")
                else:
                    port_list.append(container_port)

            result.append({
                "id": c.short_id,
                "full_id": c.id,
                "name": c.name,
                "image": ", ".join(c.image.tags) if c.image.tags else c.image.short_id,
                "status": c.status,
                "state": c.attrs.get("State", {}).get("Status", c.status),
                "ports": ", ".join(port_list) if port_list else "—",
                "created": c.attrs.get("Created", ""),
                "command": c.attrs.get("Config", {}).get("Cmd", []),
            })
        return result

    @_handle_errors
    async def start_container(self, container_id: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.start)

    @_handle_errors
    async def stop_container(self, container_id: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.stop)

    @_handle_errors
    async def restart_container(self, container_id: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.restart)

    @_handle_errors
    async def pause_container(self, container_id: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.pause)

    @_handle_errors
    async def unpause_container(self, container_id: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.unpause)

    @_handle_errors
    async def remove_container(self, container_id: str, force: bool = False) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.remove, force=force)

    @_handle_errors
    async def rename_container(self, container_id: str, new_name: str) -> None:
        container = await self._run_sync(self.client.containers.get, container_id)
        await self._run_sync(container.rename, new_name)

    @_handle_errors
    async def inspect_container(self, container_id: str) -> dict:
        container = await self._run_sync(self.client.containers.get, container_id)
        return container.attrs

    @_handle_errors
    async def container_logs(
        self, container_id: str, tail: int = 500, timestamps: bool = False
    ) -> str:
        container = await self._run_sync(self.client.containers.get, container_id)
        logs = await self._run_sync(
            container.logs,
            stdout=True,
            stderr=True,
            tail=tail,
            timestamps=timestamps,
            stream=False,
        )
        if isinstance(logs, bytes):
            return logs.decode("utf-8", errors="replace")
        return logs or ""

    @_handle_errors
    async def container_stats(self, container_id: str) -> dict:
        """Get a single stats snapshot for a container."""
        container = await self._run_sync(self.client.containers.get, container_id)
        stats = await self._run_sync(container.stats, stream=False)
        return self._parse_stats(stats)

    def _parse_stats(self, stats: dict) -> dict:
        """Parse raw Docker stats into a clean dict."""
        cpu_delta = (
            stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            - stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0) - stats.get(
            "precpu_stats", {}
        ).get("system_cpu_usage", 0)
        num_cpus = stats.get("cpu_stats", {}).get("online_cpus", 1) or 1

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        mem_usage = stats.get("memory_stats", {}).get("usage", 0)
        mem_limit = stats.get("memory_stats", {}).get("limit", 1)
        mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0

        net_rx = 0
        net_tx = 0
        networks = stats.get("networks", {})
        for iface_stats in networks.values():
            net_rx += iface_stats.get("rx_bytes", 0)
            net_tx += iface_stats.get("tx_bytes", 0)

        block_read = 0
        block_write = 0
        for entry in stats.get("blkio_stats", {}).get("io_service_bytes_recursive", []) or []:
            if entry.get("op") == "read":
                block_read += entry.get("value", 0)
            elif entry.get("op") == "write":
                block_write += entry.get("value", 0)

        return {
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage": mem_usage,
            "mem_limit": mem_limit,
            "mem_percent": round(mem_percent, 2),
            "net_rx": net_rx,
            "net_tx": net_tx,
            "block_read": block_read,
            "block_write": block_write,
            "pids": stats.get("pids_stats", {}).get("current", 0),
        }

    @_handle_errors
    async def exec_in_container(self, container_id: str, command: str) -> str:
        """Execute a command in a container and return output."""
        container = await self._run_sync(self.client.containers.get, container_id)
        result = await self._run_sync(
            container.exec_run, command, tty=True, demux=False
        )
        output = result.output
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return output or ""

    @_handle_errors
    async def create_container(self, config: dict) -> str:
        """Create a container from a configuration dict. Returns the container ID."""
        image = config.pop("image")
        name = config.pop("name", None)
        command = config.pop("command", None)
        ports = config.pop("ports", None)
        volumes = config.pop("volumes", None)
        environment = config.pop("environment", None)
        restart_policy = config.pop("restart_policy", None)
        network = config.pop("network", None)
        mem_limit = config.pop("mem_limit", None)
        cpu_count = config.pop("cpu_count", None)
        privileged = config.pop("privileged", False)
        auto_remove = config.pop("auto_remove", False)
        detach = config.pop("detach", True)

        kwargs: dict[str, Any] = {"detach": detach}
        if name:
            kwargs["name"] = name
        if command:
            kwargs["command"] = command
        if ports:
            kwargs["ports"] = ports
        if volumes:
            kwargs["volumes"] = volumes
        if environment:
            kwargs["environment"] = environment
        if restart_policy:
            kwargs["restart_policy"] = restart_policy
        if network:
            kwargs["network"] = network
        if mem_limit:
            kwargs["mem_limit"] = mem_limit
        if cpu_count:
            kwargs["cpu_count"] = cpu_count
        if privileged:
            kwargs["privileged"] = privileged
        if auto_remove:
            kwargs["auto_remove"] = auto_remove

        container = await self._run_sync(self.client.containers.create, image, **kwargs)
        return container.short_id

    # ── Image Operations ──────────────────────────────────────────────

    @_handle_errors
    async def list_images(self) -> list[dict]:
        images = await self._run_sync(self.client.images.list, all=False)
        result = []
        for img in images:
            tags = img.tags if img.tags else ["<none>:<none>"]
            for tag in tags:
                parts = tag.rsplit(":", 1)
                repo = parts[0] if len(parts) > 1 else tag
                tag_name = parts[1] if len(parts) > 1 else "latest"
                result.append({
                    "id": img.short_id.replace("sha256:", ""),
                    "full_id": img.id,
                    "repository": repo,
                    "tag": tag_name,
                    "size": img.attrs.get("Size", 0),
                    "created": img.attrs.get("Created", ""),
                })
        return result

    @_handle_errors
    async def pull_image(self, repository: str, tag: str = "latest") -> str:
        """Pull an image. Returns the image ID."""
        image = await self._run_sync(self.client.images.pull, repository, tag=tag)
        return image.short_id

    @_handle_errors
    async def remove_image(self, image_id: str, force: bool = False) -> None:
        await self._run_sync(self.client.images.remove, image_id, force=force)

    @_handle_errors
    async def tag_image(self, image_id: str, repository: str, tag: str = "latest") -> None:
        image = await self._run_sync(self.client.images.get, image_id)
        await self._run_sync(image.tag, repository, tag=tag)

    @_handle_errors
    async def inspect_image(self, image_id: str) -> dict:
        image = await self._run_sync(self.client.images.get, image_id)
        return image.attrs

    @_handle_errors
    async def image_history(self, image_id: str) -> list[dict]:
        image = await self._run_sync(self.client.images.get, image_id)
        return await self._run_sync(image.history)

    @_handle_errors
    async def build_image(
        self, path: str, tag: str | None = None, dockerfile: str = "Dockerfile"
    ) -> str:
        """Build an image from a Dockerfile. Returns the image ID."""
        image, _ = await self._run_sync(
            self.client.images.build,
            path=path,
            tag=tag,
            dockerfile=dockerfile,
            rm=True,
        )
        return image.short_id

    # ── Volume Operations ─────────────────────────────────────────────

    @_handle_errors
    async def list_volumes(self) -> list[dict]:
        response = await self._run_sync(self.client.volumes.list)
        result = []
        for v in response:
            result.append({
                "name": v.name,
                "driver": v.attrs.get("Driver", ""),
                "mountpoint": v.attrs.get("Mountpoint", ""),
                "created": v.attrs.get("CreatedAt", ""),
                "labels": v.attrs.get("Labels", {}),
            })
        return result

    @_handle_errors
    async def create_volume(self, name: str, driver: str = "local", labels: dict | None = None) -> str:
        vol = await self._run_sync(
            self.client.volumes.create, name=name, driver=driver, labels=labels or {}
        )
        return vol.name

    @_handle_errors
    async def remove_volume(self, name: str, force: bool = False) -> None:
        vol = await self._run_sync(self.client.volumes.get, name)
        await self._run_sync(vol.remove, force=force)

    @_handle_errors
    async def inspect_volume(self, name: str) -> dict:
        vol = await self._run_sync(self.client.volumes.get, name)
        return vol.attrs

    # ── Network Operations ────────────────────────────────────────────

    @_handle_errors
    async def list_networks(self) -> list[dict]:
        networks = await self._run_sync(self.client.networks.list)
        result = []
        for n in networks:
            containers = n.attrs.get("Containers", {}) or {}
            result.append({
                "id": n.short_id,
                "full_id": n.id,
                "name": n.name,
                "driver": n.attrs.get("Driver", ""),
                "scope": n.attrs.get("Scope", ""),
                "containers": len(containers),
                "internal": n.attrs.get("Internal", False),
                "ipam": n.attrs.get("IPAM", {}),
            })
        return result

    @_handle_errors
    async def create_network(
        self, name: str, driver: str = "bridge", internal: bool = False
    ) -> str:
        net = await self._run_sync(
            self.client.networks.create, name=name, driver=driver, internal=internal
        )
        return net.short_id

    @_handle_errors
    async def remove_network(self, network_id: str) -> None:
        net = await self._run_sync(self.client.networks.get, network_id)
        await self._run_sync(net.remove)

    @_handle_errors
    async def inspect_network(self, network_id: str) -> dict:
        net = await self._run_sync(self.client.networks.get, network_id)
        return net.attrs

    # ── System Operations ─────────────────────────────────────────────

    @_handle_errors
    async def system_info(self) -> dict:
        return await self._run_sync(self.client.info)

    @_handle_errors
    async def disk_usage(self) -> dict:
        return await self._run_sync(self.client.df)

    @_handle_errors
    async def prune_containers(self) -> dict:
        return await self._run_sync(self.client.containers.prune)

    @_handle_errors
    async def prune_images(self, dangling_only: bool = True) -> dict:
        filters = {"dangling": dangling_only}
        return await self._run_sync(self.client.images.prune, filters=filters)

    @_handle_errors
    async def prune_volumes(self) -> dict:
        return await self._run_sync(self.client.volumes.prune)

    @_handle_errors
    async def prune_networks(self) -> dict:
        return await self._run_sync(self.client.networks.prune)

    @_handle_errors
    async def prune_system(self) -> dict:
        """Prune everything: containers, images, volumes, networks."""
        results = {}
        results["containers"] = await self._run_sync(self.client.containers.prune)
        results["images"] = await self._run_sync(
            self.client.images.prune, filters={"dangling": False}
        )
        results["volumes"] = await self._run_sync(self.client.volumes.prune)
        results["networks"] = await self._run_sync(self.client.networks.prune)
        return results

    # ── Utility ───────────────────────────────────────────────────────

    @staticmethod
    def format_bytes(size: int | float) -> str:
        """Format byte count to human-readable string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size) < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    @staticmethod
    def format_status(status: str) -> tuple[str, str]:
        """Return (display_text, css_class) for a container status.

        Uses professional text-based labels instead of emoji indicators.
        """
        status_lower = status.lower()
        status_map = {
            "running": ("▸ RUNNING", "status-running"),
            "exited": ("■ EXITED", "status-exited"),
            "stopped": ("■ STOPPED", "status-exited"),
            "paused": ("‖ PAUSED", "status-paused"),
            "created": ("◆ CREATED", "status-created"),
            "restarting": ("↻ RESTARTING", "status-restarting"),
            "removing": ("✕ REMOVING", "status-removing"),
            "dead": ("✕ DEAD", "status-dead"),
        }
        return status_map.get(status_lower, (f"? {status.upper()}", "status-unknown"))
