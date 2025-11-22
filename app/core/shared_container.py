"""
共享容器管理器

所有用户共享一个长期运行的 Docker 容器，通过用户目录隔离。
文件系统在容器内，通过 Docker API 操作。
"""

import os
import tarfile
from io import BytesIO

from loguru import logger

import docker
from docker.errors import DockerException, NotFound

# Docker 配置
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "deepagentschat-tools:latest")
CONTAINER_NAME = "deepagentschat-shared-tools"
WORKSPACE_VOLUME = "deepagentschat-workspace"


class SharedContainerManager:
    """管理共享的长期运行容器"""

    def __init__(self):
        self.client = None
        self.container = None
        self._init_client()

    def _init_client(self):
        """初始化 Docker 客户端"""
        try:
            self.client = docker.from_env()  # type: ignore
            self.client.ping()
            logger.info("✅ Docker client initialized")
        except DockerException as e:
            logger.error(f"❌ Failed to initialize Docker client: {e}")
            raise RuntimeError(f"Docker not available: {e}") from e

    def ensure_container(self):
        """确保共享容器正在运行"""
        if self.container:
            try:
                self.container.reload()
                if self.container.status == "running":
                    return self.container
            except NotFound:
                pass

        # 尝试找到现有容器
        try:
            self.container = self.client.containers.get(CONTAINER_NAME)  # type: ignore
            if self.container.status != "running":
                logger.info(f"Starting existing container: {CONTAINER_NAME}")
                self.container.start()
            else:
                logger.info(f"Found running container: {CONTAINER_NAME}")
            return self.container
        except NotFound:
            pass

        # 创建新容器
        logger.info(f"Creating new shared container: {CONTAINER_NAME}")
        return self._create_container()

    def _create_container(self):
        """创建共享容器"""
        # 确保 Volume 存在
        try:
            self.client.volumes.get(WORKSPACE_VOLUME)  # type: ignore
            logger.info(f"Using existing volume: {WORKSPACE_VOLUME}")
        except NotFound:
            self.client.volumes.create(WORKSPACE_VOLUME)  # type: ignore
            logger.info(f"Created new volume: {WORKSPACE_VOLUME}")

        # 创建容器
        self.container = self.client.containers.run(  # type: ignore
            image=DOCKER_IMAGE,
            name=CONTAINER_NAME,
            command="tail -f /dev/null",  # 保持运行
            detach=True,
            volumes={WORKSPACE_VOLUME: {"bind": "/workspace", "mode": "rw"}},
            network_mode=os.getenv("DOCKER_NETWORK_MODE", "none"),
            mem_limit=os.getenv("DOCKER_MEMORY_LIMIT", "1g"),
            cpu_period=100000,
            cpu_quota=int(float(os.getenv("DOCKER_CPU_LIMIT", "2.0")) * 100000),
            user="1000:1000",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            restart_policy={"Name": "unless-stopped"},  # 自动重启
        )

        logger.info(f"✅ Created shared container: {CONTAINER_NAME}")
        return self.container

    def exec_command(
        self, user_id: str, command: str, timeout: int = 30, workdir: str | None = None
    ) -> tuple[str, int]:
        """
        在共享容器中执行命令

        Args:
            user_id: 用户 ID（用于确定工作目录）
            command: 要执行的命令
            timeout: 超时时间（秒）
            workdir: 工作目录（默认为用户目录）

        Returns:
            tuple[str, int]: (输出, 退出码)
        """
        container = self.ensure_container()

        # 确定工作目录
        if workdir is None:
            workdir = f"/workspace/{user_id}"

        # 确保用户目录存在
        self._ensure_user_dir(user_id)

        # 执行命令
        try:
            exec_result = container.exec_run(
                cmd=["bash", "-c", command],
                workdir=workdir,
                user="tooluser",
                demux=True,
            )

            stdout, stderr = exec_result.output
            exit_code = exec_result.exit_code

            # 隐藏绝对路径，让 Agent 对 user_id 无感
            sensitive_path = f"/workspace/{user_id}"

            output = ""
            if stdout:
                out_str = stdout.decode("utf-8", errors="replace")
                out_str = out_str.replace(sensitive_path, ".")
                output += out_str
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                stderr_text = stderr_text.replace(sensitive_path, ".")
                if stderr_text.strip():
                    output += f"\n[STDERR]:\n{stderr_text}"

            return output, exit_code

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            raise

    def _ensure_user_dir(self, user_id: str):
        """确保用户目录存在"""
        if user_id == "root":
            return

        try:
            # 直接使用 container.exec_run 避免递归调用 exec_command
            # 初始化脚本：创建目录并复制工具
            # 注意：容器启用了 cap_drop=["ALL"]，root 可能没有权限操作，
            # 但 /workspace 属于 tooluser，所以我们直接用 tooluser 执行
            init_cmd = (
                f"mkdir -p /workspace/{user_id} && "
                f"if [ -d /opt/tools ] && [ ! -d /workspace/{user_id}/.tools ]; then "
                f"cp -r /opt/tools /workspace/{user_id}/.tools; fi"
            )

            container = self.ensure_container()
            container.exec_run(
                cmd=["bash", "-c", init_cmd],
                user="tooluser",
                workdir="/workspace",
            )
        except Exception as e:
            logger.warning(f"Failed to ensure user dir: {e}")

    def upload_file(self, user_id: str, file_content: bytes, filename: str) -> bool:
        """
        上传文件到用户目录

        Args:
            user_id: 用户 ID
            file_content: 文件内容
            filename: 文件名

        Returns:
            bool: 是否成功
        """
        container = self.ensure_container()
        self._ensure_user_dir(user_id)

        try:
            # 创建 tar 包
            tar_stream = BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                # 创建文件信息
                tarinfo = tarfile.TarInfo(name=filename)
                tarinfo.size = len(file_content)
                tarinfo.mode = 0o644
                tarinfo.uid = 1000
                tarinfo.gid = 1000

                # 添加文件到 tar
                tar.addfile(tarinfo, BytesIO(file_content))

            tar_stream.seek(0)

            # 上传到容器
            container.put_archive(path=f"/workspace/{user_id}", data=tar_stream)

            logger.info(f"Uploaded file: {filename} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False

    def download_file(self, user_id: str, filename: str) -> bytes | None:
        """
        从用户目录下载文件

        Args:
            user_id: 用户 ID
            filename: 文件名

        Returns:
            bytes | None: 文件内容，失败返回 None
        """
        container = self.ensure_container()

        try:
            # 从容器获取文件
            bits, stat = container.get_archive(f"/workspace/{user_id}/{filename}")

            # 解析 tar 包
            tar_stream = BytesIO(b"".join(bits))
            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                # 获取文件
                member = tar.getmembers()[0]
                file_obj = tar.extractfile(member)
                if file_obj:
                    content = file_obj.read()
                    logger.info(f"Downloaded file: {filename} for user {user_id}")
                    return content

            return None

        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None

    def list_files(self, user_id: str, subdir: str = "") -> list[dict]:
        """
        列出用户目录下的文件

        Args:
            user_id: 用户 ID
            subdir: 子目录（相对于用户目录）

        Returns:
            list[dict]: 文件列表
        """
        # 构建路径
        path = f"/workspace/{user_id}"
        if subdir:
            path = f"{path}/{subdir.lstrip('/')}"

        # 执行 ls 命令
        output, exit_code = self.exec_command(
            user_id=user_id,
            command=f"ls -lAh --time-style=long-iso {path} 2>/dev/null || echo 'EMPTY'",
            workdir="/workspace",
        )

        if exit_code != 0 or output.strip() == "EMPTY":
            return []

        # 解析输出
        files = []
        for line in output.strip().split("\n"):
            if not line or line.startswith("total"):
                continue

            # ls -lAh --time-style=long-iso 输出格式：
            # 权限 链接数 所有者 组 大小 日期 时间 文件名
            # -rw-r--r-- 1 tooluser tooluser 595K 2025-11-22 16:30 filename.docx
            parts = line.split(maxsplit=7)
            if len(parts) < 8:
                continue

            permissions = parts[0]
            size = parts[4]
            date = parts[5]
            time = parts[6]
            filename = parts[7]

            # 跳过 . 和 ..
            if filename in [".", ".."]:
                continue

            files.append(
                {
                    "filename": filename,
                    "size": size,
                    "modified": f"{date} {time}",
                    "is_dir": permissions.startswith("d"),
                    "permissions": permissions,
                }
            )

        return files

    def delete_file(self, user_id: str, filename: str) -> bool:
        """
        删除用户文件

        Args:
            user_id: 用户 ID
            filename: 文件名

        Returns:
            bool: 是否成功
        """
        output, exit_code = self.exec_command(
            user_id=user_id, command=f"rm -rf {filename}", workdir=f"/workspace/{user_id}"
        )

        return exit_code == 0

    def get_container_stats(self) -> dict:
        """获取容器统计信息"""
        container = self.ensure_container()
        try:
            stats = container.stats(stream=False)
            return {
                "cpu_usage": stats["cpu_stats"]["cpu_usage"]["total_usage"],
                "memory_usage": stats["memory_stats"]["usage"],
                "memory_limit": stats["memory_stats"]["limit"],
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def stop_container(self):
        """停止共享容器"""
        if self.container:
            try:
                self.container.stop()
                logger.info(f"Stopped container: {CONTAINER_NAME}")
            except Exception as e:
                logger.error(f"Failed to stop container: {e}")

    def remove_container(self):
        """删除共享容器"""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                logger.info(f"Removed container: {CONTAINER_NAME}")
            except Exception as e:
                logger.error(f"Failed to remove container: {e}")


# 全局单例
_shared_container_manager = None


def get_shared_container_manager() -> SharedContainerManager:
    """获取共享容器管理器单例"""
    global _shared_container_manager
    if _shared_container_manager is None:
        _shared_container_manager = SharedContainerManager()
    return _shared_container_manager
