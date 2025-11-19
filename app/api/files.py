"""
文件管理 API 路由

提供文件上传、下载、列表等功能
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from app.backends import FilesystemSandboxBackend
from app.core.deps import CurrentUser
from app.models.base import BaseResponse

router = APIRouter(prefix="/files", tags=["Files"])


class FileInfo(BaseModel):
    """文件信息"""

    filename: str
    size: int
    path: str


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


def get_user_backend(user_id: uuid.UUID) -> FilesystemSandboxBackend:
    """
    获取用户的文件系统后端

    Args:
        user_id: 用户 ID

    Returns:
        FilesystemSandboxBackend: 用户的文件系统后端
    """
    return FilesystemSandboxBackend(
        root_dir=f"/tmp/{user_id}",
        virtual_mode=False,  # 使用实际文件系统以支持文件上传
    )


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
        # 读取文件内容
        content = await file.read()

        # 获取用户的后端
        backend = get_user_backend(current_user.id)

        # 确保文件名安全（移除路径分隔符）
        safe_filename = Path(file.filename or "unnamed").name

        # 写入文件
        backend.write(safe_filename, content.decode("utf-8") if content else "")

        logger.info(f"User {current_user.id} uploaded file: {safe_filename} ({len(content)} bytes)")

        return BaseResponse(
            success=True,
            code=200,
            msg="文件上传成功",
            data=UploadResponse(
                filename=safe_filename,
                path=f"/tmp/{current_user.id}/{safe_filename}",
                size=len(content),
                message=f"文件 {safe_filename} 已上传到您的工作目录",
            ),
        )
    except UnicodeDecodeError:
        # 如果是二进制文件，直接写入原始字节
        try:
            # 对于二进制文件，我们需要直接写入文件系统
            backend = get_user_backend(current_user.id)
            safe_filename = Path(file.filename or "unnamed").name

            # 使用 Path 直接写入二进制文件
            file_path = Path(backend.cwd) / safe_filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 重新读取文件（因为之前已经读过了）
            await file.seek(0)
            content = await file.read()

            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"User {current_user.id} uploaded binary file: {safe_filename} ({len(content)} bytes)")

            return BaseResponse(
                success=True,
                code=200,
                msg="文件上传成功",
                data=UploadResponse(
                    filename=safe_filename,
                    path=str(file_path),
                    size=len(content),
                    message=f"文件 {safe_filename} 已上传到您的工作目录",
                ),
            )
        except Exception as e:
            logger.error(f"Failed to upload binary file: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}") from e


@router.get("/list", response_model=BaseResponse[FileListResponse])
async def list_files(current_user: CurrentUser):
    """
    列出用户工作目录中的所有文件

    Args:
        current_user: 当前登录用户

    Returns:
        FileListResponse: 文件列表
    """
    try:
        backend = get_user_backend(current_user.id)

        # 使用 execute 命令列出文件
        result = backend.execute("find . -type f -exec ls -lh {} \\;")

        if result.exit_code != 0:
            logger.warning(f"Failed to list files for user {current_user.id}: {result.output}")
            return BaseResponse(
                success=True,
                code=200,
                msg="获取文件列表成功",
                data=FileListResponse(files=[], total=0),
            )

        # 解析文件列表
        files = []
        for line in result.output.strip().split("\n"):
            if not line or line == "(no output)":
                continue

            parts = line.split()
            if len(parts) >= 9:
                size_str = parts[4]
                filename = " ".join(parts[8:])

                # 转换文件大小
                try:
                    if size_str.endswith("K"):
                        size = int(float(size_str[:-1]) * 1024)
                    elif size_str.endswith("M"):
                        size = int(float(size_str[:-1]) * 1024 * 1024)
                    elif size_str.endswith("G"):
                        size = int(float(size_str[:-1]) * 1024 * 1024 * 1024)
                    else:
                        size = int(size_str)
                except (ValueError, IndexError):
                    size = 0

                files.append(
                    FileInfo(
                        filename=Path(filename).name,
                        size=size,
                        path=filename,
                    )
                )

        return BaseResponse(
            success=True,
            code=200,
            msg="获取文件列表成功",
            data=FileListResponse(files=files, total=len(files)),
        )
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}") from e


@router.get("/read/{filename}")
async def read_file(filename: str, current_user: CurrentUser):
    """
    读取用户工作目录中的文件内容

    Args:
        filename: 文件名
        current_user: 当前登录用户

    Returns:
        str: 文件内容
    """
    try:
        backend = get_user_backend(current_user.id)

        # 确保文件名安全
        safe_filename = Path(filename).name

        # 读取文件
        content = backend.read(safe_filename)

        return BaseResponse(
            success=True,
            code=200,
            msg="读取文件成功",
            data={"filename": safe_filename, "content": content},
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"文件不存在: {filename}") from e
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}") from e


@router.delete("/{filename}")
async def delete_file(filename: str, current_user: CurrentUser):
    """
    删除用户工作目录中的文件

    Args:
        filename: 文件名
        current_user: 当前登录用户

    Returns:
        dict: 删除结果
    """
    try:
        backend = get_user_backend(current_user.id)

        # 确保文件名安全
        safe_filename = Path(filename).name

        # 删除文件
        result = backend.execute(f"rm -f {safe_filename}")

        if result.exit_code != 0:
            raise HTTPException(status_code=500, detail=f"删除文件失败: {result.output}")

        logger.info(f"User {current_user.id} deleted file: {safe_filename}")

        return BaseResponse(
            success=True,
            code=200,
            msg="删除文件成功",
            data={"filename": safe_filename, "message": f"文件 {safe_filename} 已删除"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}") from e


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
        backend = get_user_backend(current_user.id)

        # 列出所有文件
        result_before = backend.execute("ls -1")
        files_before = result_before.output.strip().split("\n") if result_before.output.strip() else []
        file_count = len([f for f in files_before if f and f != "(no output)"])

        # 删除所有文件（不删除目录）
        result = backend.execute("find . -type f -delete")

        if result.exit_code != 0:
            raise HTTPException(status_code=500, detail=f"清空文件失败: {result.output}")

        logger.info(f"User {current_user.id} cleared all files ({file_count} files deleted)")

        return BaseResponse(
            success=True,
            code=200,
            msg="清空文件成功",
            data={
                "message": f"已清空工作目录，删除了 {file_count} 个文件",
                "deleted_count": file_count,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear files: {e}")
        raise HTTPException(status_code=500, detail=f"清空文件失败: {str(e)}") from e
