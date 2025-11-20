"""FilesystemSandboxBackend: FilesystemBackend with command execution support."""

import re
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol
from loguru import logger

if TYPE_CHECKING:
    pass


class FilesystemSandboxBackend(FilesystemBackend, SandboxBackendProtocol):
    """FilesystemBackend with command execution support.

    Extends FilesystemBackend to implement SandboxBackendProtocol by adding
    command execution capabilities. Commands are executed in the local system
    environment, with the working directory set to the backend's root_dir.

    Features:
    - ✅ Real filesystem access (read/write actual files)
    - ✅ Command execution in specified directory
    - ✅ Configurable timeout and output limits
    - ✅ Support for virtual_mode (path sandboxing)

    Warning:
        This backend executes commands directly on the host system without
        isolation. Use with caution and only with trusted agents. For production
        use, consider using DockerSandboxBackend instead.

    Example:
        ```python
        from app.backends.filesystem_sandbox import FilesystemSandboxBackend

        # Create backend with specific root directory
        backend = FilesystemSandboxBackend(
            root_dir="/path/to/workspace",
            virtual_mode=True,  # Enable path sandboxing
        )

        # Use with Agent
        agent = create_agent(model, tools=tools, middleware=[FilesystemMiddleware(backend=backend)])
        ```
    """

    def __init__(
        self,
        root_dir: str | Path | None = None,
        virtual_mode: bool = False,
        max_file_size_mb: int = 10,
        max_output_size: int = 100000,
        command_timeout: int = 30,
    ):
        """Initialize FilesystemSandboxBackend.

        Args:
            root_dir: Root directory for file operations. If not provided, uses cwd.
            virtual_mode: Enable path sandboxing (prevent access outside root_dir).
            max_file_size_mb: Maximum file size in MB for read operations.
            max_output_size: Maximum command output size in characters.
            command_timeout: Command execution timeout in seconds.
        """
        super().__init__(
            root_dir=root_dir,
            virtual_mode=virtual_mode,
            max_file_size_mb=max_file_size_mb,
        )
        self._id = str(uuid.uuid4())
        self.max_output_size = max_output_size
        self.command_timeout = command_timeout

    @property
    def id(self) -> str:
        """Unique identifier for this backend instance."""
        return self._id

    def execute(self, command: str) -> ExecuteResponse:
        """Execute a shell command in the root directory.

        Args:
            command: Shell command to execute.

        Returns:
            ExecuteResponse with combined stdout/stderr output and exit code.

        Note:
            Commands are executed with cwd set to self.cwd (root_dir).
            In virtual_mode, virtual absolute paths (e.g. /file.txt) are
            automatically translated to relative paths (e.g. ./file.txt).
        """
        # 在 virtual_mode 下，转换命令中的虚拟绝对路径
        if self.virtual_mode:
            command = self._translate_virtual_paths(command)

        try:
            # Execute command with timeout and cwd
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
                cwd=str(self.cwd),  # Execute in root directory
            )

            # Combine stdout and stderr
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            # Check if output needs truncation
            truncated = False
            if len(output) > self.max_output_size:
                output = output[: self.max_output_size]
                truncated = True

            return ExecuteResponse(
                output=output or "(no output)",
                exit_code=result.returncode,
                truncated=truncated,
            )

        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Error: Command execution timed out ({self.command_timeout} seconds limit)",
                exit_code=-1,
                truncated=False,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command: {str(e)}",
                exit_code=-1,
                truncated=False,
            )

    def _translate_virtual_paths(self, command: str) -> str:
        """将命令中的虚拟绝对路径转换为相对路径

        在 virtual_mode 下，Agent 使用的路径是虚拟的（如 /file.txt），
        但 shell 命令在实际文件系统中执行。此方法将虚拟路径转换为
        相对于 root_dir 的相对路径。

        Examples:
            "/file.txt" → "./file.txt"
            "/dir/file.txt" → "./dir/file.txt"
            "/usr/bin/python" → "/usr/bin/python" (系统路径不转换)

        Args:
            command: 原始命令

        Returns:
            转换后的命令
        """
        # 常见系统路径（不应被转换）
        system_paths = {
            "usr",
            "etc",
            "bin",
            "lib",
            "lib64",
            "var",
            "tmp",
            "home",
            "root",
            "opt",
            "sys",
            "proc",
            "dev",
            "mnt",
            "boot",
            "srv",
            "run",
            "snap",
            "sbin",
        }

        def replace_path(match):
            full_path = match.group(0)
            quote = match.group(1) or ""  # 保留引号
            path = match.group(2)

            # 检查是否是系统路径
            first_segment = path.lstrip("/").split("/")[0]
            if first_segment in system_paths:
                return full_path  # 保持原样

            # 转换为相对路径
            relative_path = "./" + path.lstrip("/")
            return f"{quote}{relative_path}{quote}"

        # 匹配带或不带引号的绝对路径
        # 支持: /path, "/path", '/path'
        pattern = r'(["\']?)(/[\w\-./]+)\1'

        translated = re.sub(pattern, replace_path, command)

        # 记录转换（仅在实际发生转换时）
        if translated != command:
            logger.debug(f"[VirtualPath] Translated: {command} → {translated}")

        return translated
