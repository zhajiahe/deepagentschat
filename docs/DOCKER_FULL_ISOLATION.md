# Docker 完全隔离方案

## 📋 概述

当前的 `tools_docker.py` 设计是**部分隔离**：
- ✅ 代码执行在容器内
- ❌ 文件系统挂载宿主机

你的需求是**完全隔离**：
- ✅ 代码执行在容器内
- ✅ 文件系统也在容器内

## 🎯 设计目标

### 方案对比

| 特性 | 当前方案（挂载） | 完全隔离方案 |
|------|-----------------|-------------|
| 代码执行 | 容器内 | 容器内 |
| 文件存储 | 宿主机 | 容器内 |
| 文件持久化 | 自动（宿主机） | 需要 Docker Volume |
| 隔离性 | 中等 | 最强 |
| 性能 | 高 | 中等 |
| 复杂度 | 低 | 高 |

## 🏗️ 完全隔离架构

### 架构 1: 长期运行容器 + Docker Volume

```
FastAPI App
    ↓
Docker Client API
    ↓
Long-Running Container (per user)
    ├── Docker Volume: /workspace
    ├── 用户文件存储在容器内
    └── 执行命令
```

**特点**:
- 每个用户一个长期运行的容器
- 使用 Docker Volume 持久化数据
- files.py 通过 Docker API 操作容器内文件

### 架构 2: 临时容器 + Docker Volume

```
FastAPI App
    ↓
Docker Client API
    ↓
Temporary Container (per request)
    ├── Docker Volume: /workspace (持久化)
    ├── 执行命令
    └── 容器销毁（Volume 保留）
```

**特点**:
- 每次请求创建临时容器
- Volume 在容器间共享
- 更安全但启动慢

## 💻 实现方案

### 方案 1: 长期运行容器（推荐）

#### 1.1 容器管理器

```python
# app/core/docker_manager.py
import docker
from docker.types import Mount
from loguru import logger

class UserContainerManager:
    """管理用户的长期运行容器"""

    def __init__(self):
        self.client = docker.from_env()
        self.containers = {}  # {user_id: container}

    def get_or_create_container(self, user_id: str):
        """获取或创建用户容器"""
        if user_id in self.containers:
            container = self.containers[user_id]
            # 检查容器是否还在运行
            try:
                container.reload()
                if container.status == "running":
                    return container
            except:
                pass

        # 创建新容器
        volume_name = f"user_{user_id}_workspace"

        # 创建 Volume（如果不存在）
        try:
            self.client.volumes.get(volume_name)
        except docker.errors.NotFound:
            self.client.volumes.create(volume_name)

        # 创建容器
        container = self.client.containers.run(
            image="deepagentschat-tools:latest",
            command="tail -f /dev/null",  # 保持运行
            detach=True,
            name=f"user_{user_id}",
            volumes={volume_name: {"bind": "/workspace", "mode": "rw"}},
            network_mode="none",
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=100000,
            user="1000:1000",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            remove=False,  # 不自动删除
        )

        self.containers[user_id] = container
        logger.info(f"Created container for user {user_id}")
        return container

    def exec_command(self, user_id: str, command: str, timeout: int = 30):
        """在用户容器中执行命令"""
        container = self.get_or_create_container(user_id)

        # 执行命令
        exec_result = container.exec_run(
            cmd=["bash", "-c", command],
            workdir="/workspace",
            user="tooluser",
            demux=True,
        )

        stdout, stderr = exec_result.output
        exit_code = exec_result.exit_code

        output = ""
        if stdout:
            output += stdout.decode("utf-8")
        if stderr:
            output += f"\n[STDERR]:\n{stderr.decode('utf-8')}"
        if exit_code != 0:
            output += f"\n[Exit Code: {exit_code}]"

        return output

    def copy_to_container(self, user_id: str, local_path: str, container_path: str):
        """复制文件到容器"""
        container = self.get_or_create_container(user_id)

        import tarfile
        import io

        # 创建 tar 包
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tar.add(local_path, arcname=os.path.basename(container_path))

        tar_stream.seek(0)
        container.put_archive(
            path=os.path.dirname(container_path) or "/workspace",
            data=tar_stream
        )

    def copy_from_container(self, user_id: str, container_path: str, local_path: str):
        """从容器复制文件"""
        container = self.get_or_create_container(user_id)

        bits, stat = container.get_archive(container_path)

        import tarfile
        import io

        tar_stream = io.BytesIO(b"".join(bits))
        with tarfile.open(fileobj=tar_stream, mode='r') as tar:
            tar.extractall(path=os.path.dirname(local_path))

    def list_files(self, user_id: str, path: str = "/workspace"):
        """列出容器内文件"""
        container = self.get_or_create_container(user_id)

        exec_result = container.exec_run(
            cmd=["ls", "-la", path],
            workdir="/workspace",
        )

        return exec_result.output.decode("utf-8")

    def cleanup_container(self, user_id: str):
        """清理用户容器"""
        if user_id in self.containers:
            try:
                self.containers[user_id].stop()
                self.containers[user_id].remove()
                del self.containers[user_id]
                logger.info(f"Cleaned up container for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup container: {e}")

# 全局实例
container_manager = UserContainerManager()
```

#### 1.2 修改 files.py

```python
# app/api/files.py
from app.core.docker_manager import container_manager

@router.post("/upload")
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """上传文件到用户容器"""
    try:
        # 保存到临时文件
        temp_file = f"/tmp/{file.filename}"
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        # 复制到容器
        container_manager.copy_to_container(
            user_id=str(current_user.id),
            local_path=temp_file,
            container_path=f"/workspace/{file.filename}"
        )

        # 删除临时文件
        os.remove(temp_file)

        return BaseResponse(
            success=True,
            data={
                "filename": file.filename,
                "size": len(content),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_files(current_user: CurrentUser):
    """列出容器内文件"""
    try:
        output = container_manager.list_files(
            user_id=str(current_user.id)
        )

        # 解析 ls 输出
        files = []
        for line in output.split("\n")[1:]:  # 跳过第一行（总计）
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 9:
                files.append({
                    "filename": parts[8],
                    "size": int(parts[4]),
                    "is_dir": parts[0].startswith("d"),
                })

        return BaseResponse(
            success=True,
            data={"files": files, "total": len(files)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: CurrentUser,
):
    """从容器下载文件"""
    try:
        # 复制到临时文件
        temp_file = f"/tmp/{filename}"
        container_manager.copy_from_container(
            user_id=str(current_user.id),
            container_path=f"/workspace/{filename}",
            local_path=temp_file
        )

        return FileResponse(
            path=temp_file,
            filename=filename,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")
```

#### 1.3 修改 tools_docker.py

```python
# app/tools_docker.py
from app.core.docker_manager import container_manager

@tool(parse_docstring=True)
async def shell_exec(
    command: str,
    runtime: ToolRuntime[UserContext],
    timeout: int = 30,
) -> str:
    """在用户容器中执行命令"""
    try:
        user_id = runtime.context.user_id if runtime and runtime.context else None
        if not user_id:
            return "[错误] 需要用户上下文"

        # 在用户容器中执行
        output = container_manager.exec_command(
            user_id=user_id,
            command=command,
            timeout=timeout
        )

        return output
    except Exception as e:
        return f"[错误] {str(e)}"
```

### 方案 2: 临时容器 + Volume（更安全）

```python
# 每次执行创建临时容器，但使用持久化 Volume

async def run_in_isolated_container(
    user_id: str,
    command: str,
    timeout: int = 30
):
    """在临时容器中执行，使用持久化 Volume"""
    client = docker.from_env()
    volume_name = f"user_{user_id}_workspace"

    # 确保 Volume 存在
    try:
        client.volumes.get(volume_name)
    except docker.errors.NotFound:
        client.volumes.create(volume_name)

    # 创建临时容器
    container = client.containers.run(
        image="deepagentschat-tools:latest",
        command=["bash", "-c", command],
        volumes={volume_name: {"bind": "/workspace", "mode": "rw"}},
        working_dir="/workspace",
        detach=True,
        remove=True,  # 执行完自动删除
        # ... 其他安全配置
    )

    # 等待执行完成
    result = container.wait(timeout=timeout)
    logs = container.logs().decode("utf-8")

    return logs
```

## 📊 方案对比

| 特性 | 长期运行容器 | 临时容器 + Volume |
|------|-------------|------------------|
| 启动速度 | 快（容器已运行） | 慢（每次创建） |
| 资源占用 | 高（持续运行） | 低（按需创建） |
| 隔离性 | 中等 | 最强 |
| 复杂度 | 中等 | 低 |
| 适用场景 | 频繁操作 | 偶尔操作 |

## 🚀 实施步骤

### 步骤 1: 创建容器管理器

```bash
# 创建文件
touch app/core/docker_manager.py
# 实现 UserContainerManager
```

### 步骤 2: 修改 files.py

```bash
# 修改上传/下载/列表接口
# 使用 Docker API 操作容器内文件
```

### 步骤 3: 修改 tools_docker.py

```bash
# 使用容器管理器执行命令
```

### 步骤 4: 测试

```bash
# 测试文件上传
# 测试命令执行
# 测试文件下载
```

## ⚠️ 注意事项

### 1. 性能影响

- 文件上传/下载需要通过 Docker API
- 比直接文件系统操作慢
- 适合安全性要求高的场景

### 2. 资源管理

- 长期运行容器需要定期清理
- Volume 需要定期清理
- 监控容器数量和资源使用

### 3. 数据持久化

- 使用 Docker Volume 持久化数据
- Volume 独立于容器生命周期
- 需要备份策略

## 🎯 推荐方案

### 开发环境
- 使用当前的挂载方案（简单快速）

### 生产环境（中等安全）
- 使用长期运行容器 + Volume

### 生产环境（高安全）
- 使用临时容器 + Volume
- 每次请求创建新容器

## 💡 总结

完全隔离方案提供了最强的安全性，但增加了复杂度和性能开销。需要根据实际需求选择合适的方案：

- **简单场景**: 当前挂载方案
- **平衡方案**: 长期运行容器
- **高安全**: 临时容器

---

**下一步**: 你希望我实现哪个方案？
1. 长期运行容器方案（推荐）
2. 临时容器方案
3. 两者都实现，可配置选择
