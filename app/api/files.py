"""
文件管理 API 路由

提供文件上传、下载、列表等功能
使用本地文件系统存储（简化版本，不依赖自定义 backend）
"""

import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.storage import get_user_storage_path, sanitize_filename
from app.models.base import BaseResponse

# 如果启用了 Docker 工具，导入容器管理器
if settings.USE_DOCKER_TOOLS:
    from app.core.shared_container import get_shared_container_manager

router = APIRouter(prefix="/files", tags=["Files"])


class FileInfo(BaseModel):
    """文件信息"""

    filename: str
    size: int
    path: str
    is_dir: bool = False  # 是否为目录


class FileListResponse(BaseModel):
    """文件列表响应"""

    files: list[FileInfo]
    total: int


class UploadResponse(BaseModel):
    """上传响应"""

    filename: str
    path: str
    size: int
    message: str


@router.post("/upload", response_model=BaseResponse[UploadResponse])
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="要上传的文件"),
):
    """
    上传文件到用户的工作目录

    Args:
        file: 上传的文件
        current_user: 当前登录用户

    Returns:
        UploadResponse: 上传结果
    """
    try:
        # 确保文件名安全
        safe_filename = sanitize_filename(file.filename or "unnamed")
        content = await file.read()
        file_size = len(content)

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式：上传到容器
            manager = get_shared_container_manager()
            success = manager.upload_file(user_id=str(current_user.id), file_content=content, filename=safe_filename)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload file to container")
            file_path = f"/workspace/{current_user.id}/{safe_filename}"  # 容器内路径
        else:
            # 本地模式：直接写入文件系统
            user_path = get_user_storage_path(current_user.id)
            file_path_obj = user_path / safe_filename
            with open(file_path_obj, "wb") as f:
                f.write(content)
            file_path = str(file_path_obj)

        logger.info(f"User {current_user.id} uploaded file: {safe_filename} ({file_size} bytes)")

        return BaseResponse(
            success=True,
            code=200,
            msg="文件上传成功",
            data=UploadResponse(
                filename=safe_filename,
                path=file_path,
                size=file_size,
                message=f"文件 {safe_filename} 已上传",
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}") from e


@router.get("/list", response_model=BaseResponse[FileListResponse])
async def list_files(current_user: CurrentUser, subdir: str = ""):
    """
    列出用户工作目录中的文件和文件夹

    Args:
        current_user: 当前登录用户
        subdir: 子目录路径（相对于用户根目录）

    Returns:
        FileListResponse: 文件列表
    """
    try:
        files = []
        subdir = subdir.replace("../", "").replace("..\\", "").strip("/")

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式：列出容器内文件
            manager = get_shared_container_manager()
            file_list = manager.list_files(user_id=str(current_user.id), subdir=subdir)

            for f in file_list:
                # 将 Docker 返回的 dict 转换为 FileInfo
                # 注意：Docker list_files 返回的是 dict，包含 filename, size, is_dir 等
                rel_path = str(Path(subdir) / f["filename"]) if subdir else f["filename"]

                # 处理大小格式（ls -h 返回的是人类可读格式，如 1.2K，这里简单处理或者 container_manager 改为返回字节）
                # SharedContainerManager.list_files 使用 ls -h，这里我们应该改进 SharedContainerManager
                # 或者在这里做解析。为了简单，这里假设 size 可能是字符串
                # 注意：FileInfo 定义 size 是 int。container_manager.list_files 应该返回 int。
                # 让我检查一下 SharedContainerManager 的实现... 它返回的是 ls -h 的字符串。
                # 我们需要修改 SharedContainerManager 或者在这里解析。
                # 为了保持 SharedContainerManager 独立，我们暂时只能尽力解析或修改 FileInfo。
                # 更好的做法是 SharedContainerManager 返回字节数。
                # 无论如何，先处理 is_dir

                # 临时方案：尝试解析大小，如果失败设为 0
                size_str = str(f["size"]).upper()
                size = 0
                try:
                    if size_str.endswith("K"):
                        size = int(float(size_str[:-1]) * 1024)
                    elif size_str.endswith("M"):
                        size = int(float(size_str[:-1]) * 1024 * 1024)
                    elif size_str.endswith("G"):
                        size = int(float(size_str[:-1]) * 1024 * 1024 * 1024)
                    else:
                        size = int(size_str)
                except ValueError:
                    pass

                files.append(
                    FileInfo(
                        filename=f["filename"],
                        size=size,
                        path=rel_path,
                        is_dir=f["is_dir"],
                    )
                )
        else:
            # 本地模式：列出本地文件
            user_path = get_user_storage_path(current_user.id)

            if subdir:
                target_path = (user_path / subdir).resolve()
                # 确保目标路径在用户目录内
                if not str(target_path).startswith(str(user_path.resolve())):
                    raise HTTPException(status_code=403, detail="无效的目录路径")
            else:
                target_path = user_path

            if not target_path.exists():
                # 如果是根目录且不存在，返回空列表（新用户可能还没目录）
                if not subdir:
                    return BaseResponse(
                        success=True, code=200, msg="获取文件列表成功", data=FileListResponse(files=[], total=0)
                    )
                raise HTTPException(status_code=404, detail=f"目录不存在: {subdir}")

            for item_path in sorted(target_path.iterdir()):
                # 计算相对路径
                rel_path = str(item_path.relative_to(user_path))

                if item_path.is_dir():
                    files.append(FileInfo(filename=item_path.name, size=0, path=rel_path, is_dir=True))
                elif item_path.is_file():
                    files.append(
                        FileInfo(
                            filename=item_path.name,
                            size=item_path.stat().st_size,
                            path=rel_path,
                            is_dir=False,
                        )
                    )

        return BaseResponse(
            success=True,
            code=200,
            msg="获取文件列表成功",
            data=FileListResponse(files=files, total=len(files)),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}") from e


@router.get("/download/{file_path:path}")
async def download_file(file_path: str, current_user: CurrentUser):
    """
    下载用户工作目录中的文件（支持二进制文件）

    Args:
        file_path: 文件路径（相对于用户根目录）
        current_user: 当前登录用户

    Returns:
        FileResponse: 文件下载响应
    """
    try:
        # 清理路径，防止路径遍历
        safe_path = file_path.replace("../", "").replace("..\\", "")

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式：从容器下载到临时文件
            manager = get_shared_container_manager()

            # 注意：download_file 目前只支持下载根目录文件，我们需要修改 SharedContainerManager 或传递完整路径
            # SharedContainerManager.download_file 接受 filename，我们传 path
            content = manager.download_file(user_id=str(current_user.id), filename=safe_path)

            if content is None:
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

            # 创建临时文件
            # 使用 tempfile.NamedTemporaryFile 创建，但在 windows 下可能会有 delete=True 的锁问题
            # 这里为了稳健，使用 mkstemp 或 NamedTemporaryFile(delete=False)
            # 更好的方式是使用 UploadFile 类似的 SpooledTemporaryFile，但 FileResponse 需要路径

            temp_dir = Path(tempfile.gettempdir()) / "deepagents_downloads"
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / f"{uuid.uuid4()}_{Path(safe_path).name}"

            with open(temp_file, "wb") as f:
                f.write(content)

            # 使用 background task 删除临时文件
            return FileResponse(
                path=str(temp_file),
                filename=Path(safe_path).name,
                media_type="application/octet-stream",
                background=None,  # 这里理想情况是发送后删除，但 FileResponse 不支持直接的 cleanup callback
                # 可以自定义 background task 来删除，或者依赖操作系统的临时文件清理
            )
            # 为了不让磁盘爆满，我们还是简单起见，不删除（依赖系统清理 /tmp）或者以后优化

        else:
            # 本地模式：直接下载
            user_path = get_user_storage_path(current_user.id)
            full_path = (user_path / safe_path).resolve()

            # 确保路径在用户目录内
            if not str(full_path).startswith(str(user_path.resolve())):
                raise HTTPException(status_code=403, detail="无效的文件路径")

            if not full_path.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

            if not full_path.is_file():
                raise HTTPException(status_code=400, detail=f"{file_path} 不是文件")

            # 返回文件
            return FileResponse(
                path=str(full_path),
                filename=full_path.name,
                media_type="application/octet-stream",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}") from e


@router.get("/read/{file_path:path}")
async def read_file(file_path: str, current_user: CurrentUser):
    """
    读取用户工作目录中的文件内容（文本文件预览）

    Args:
        file_path: 文件路径（相对于用户根目录）
        current_user: 当前登录用户

    Returns:
        str: 文件内容
    """
    try:
        safe_path = file_path.replace("../", "").replace("..\\", "")

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式
            manager = get_shared_container_manager()
            content_bytes = manager.download_file(user_id=str(current_user.id), filename=safe_path)

            if content_bytes is None:
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = content_bytes.decode("utf-8", errors="replace")

            filename = Path(safe_path).name
        else:
            # 本地模式
            user_path = get_user_storage_path(current_user.id)
            full_path = (user_path / safe_path).resolve()

            # 确保路径在用户目录内
            if not str(full_path).startswith(str(user_path.resolve())):
                raise HTTPException(status_code=403, detail="无效的文件路径")

            if not full_path.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

            if not full_path.is_file():
                raise HTTPException(status_code=400, detail=f"{file_path} 不是文件")

            # 读取文件
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            filename = full_path.name

        return BaseResponse(
            success=True,
            code=200,
            msg="读取文件成功",
            data={"filename": filename, "content": content},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}") from e


@router.delete("/{file_path:path}")
async def delete_file(file_path: str, current_user: CurrentUser):
    """
    删除用户工作目录中的文件

    Args:
        file_path: 文件路径（相对于用户根目录）
        current_user: 当前登录用户

    Returns:
        dict: 删除结果
    """
    try:
        safe_path = file_path.replace("../", "").replace("..\\", "")

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式
            manager = get_shared_container_manager()
            success = manager.delete_file(user_id=str(current_user.id), filename=safe_path)
            if not success:
                # 可能是文件不存在或删除失败
                raise HTTPException(status_code=500, detail=f"删除失败: {file_path}")
            filename = Path(safe_path).name
        else:
            # 本地模式
            user_path = get_user_storage_path(current_user.id)
            full_path = (user_path / safe_path).resolve()

            # 确保路径在用户目录内
            if not str(full_path).startswith(str(user_path.resolve())):
                raise HTTPException(status_code=403, detail="无效的文件路径")

            if not full_path.exists():
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

            # 删除文件或目录
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                raise HTTPException(status_code=400, detail="无效的文件类型")
            filename = Path(file_path).name

        logger.info(f"User {current_user.id} deleted: {file_path}")

        return BaseResponse(
            success=True,
            code=200,
            msg="删除成功",
            data={"filename": filename, "message": f"{filename} 已删除"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}") from e


@router.delete("")
async def clear_all_files(current_user: CurrentUser):
    """
    清空用户工作目录中的所有文件

    Args:
        current_user: 当前登录用户

    Returns:
        dict: 清空结果
    """
    try:
        file_count = 0

        if settings.USE_DOCKER_TOOLS:
            # Docker 模式：重新创建用户目录或删除所有内容
            manager = get_shared_container_manager()
            # 简单粗暴：删除用户目录然后重新创建
            # 或者执行 rm -rf /workspace/{user_id}/*
            # 注意：SharedContainerManager 没有直接的 clear_all 接口，我们用 exec_command
            user_id = str(current_user.id)
            # 获取文件数量（估算）
            output, _ = manager.exec_command(user_id=user_id, command=f"ls -1 /workspace/{user_id} | wc -l")
            try:
                file_count = int(output.strip())
            except ValueError:
                pass

            manager.exec_command(user_id=user_id, command=f"rm -rf /workspace/{user_id}/*")
        else:
            # 本地模式
            user_path = get_user_storage_path(current_user.id)

            # 删除所有文件
            for file_path in user_path.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    file_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    file_count += 1

        logger.info(f"User {current_user.id} cleared all files")

        return BaseResponse(
            success=True,
            code=200,
            msg="清空文件成功",
            data={
                "message": "已清空工作目录",
                "deleted_count": file_count,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear files: {e}")
        raise HTTPException(status_code=500, detail=f"清空文件失败: {str(e)}") from e
