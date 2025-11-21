"""
文件管理 API 路由

提供文件上传、下载、列表等功能
使用本地文件系统存储（简化版本，不依赖自定义 backend）
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from app.core.deps import CurrentUser
from app.models.base import BaseResponse

router = APIRouter(prefix="/files", tags=["Files"])

# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


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


def get_user_storage_path(user_id: uuid.UUID) -> Path:
    """
    获取用户的存储目录

    Args:
        user_id: 用户 ID

    Returns:
        Path: 用户存储目录路径
    """
    user_path = STORAGE_ROOT / str(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


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
        # 获取用户存储目录
        user_path = get_user_storage_path(current_user.id)

        # 确保文件名安全（移除路径分隔符）
        safe_filename = Path(file.filename or "unnamed").name

        # 保存文件
        file_path = user_path / safe_filename
        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        file_size = len(content)
        logger.info(f"User {current_user.id} uploaded file: {safe_filename} ({file_size} bytes)")

        return BaseResponse(
            success=True,
            code=200,
            msg="文件上传成功",
            data=UploadResponse(
                filename=safe_filename,
                path=str(file_path),
                size=file_size,
                message=f"文件 {safe_filename} 已上传",
            ),
        )
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
        user_path = get_user_storage_path(current_user.id)

        files = []
        for file_path in user_path.iterdir():
            if file_path.is_file():
                files.append(
                    FileInfo(
                        filename=file_path.name,
                        size=file_path.stat().st_size,
                        path=file_path.name,
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
        user_path = get_user_storage_path(current_user.id)

        # 确保文件名安全
        safe_filename = Path(filename).name
        file_path = user_path / safe_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

        # 读取文件
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return BaseResponse(
            success=True,
            code=200,
            msg="读取文件成功",
            data={"filename": safe_filename, "content": content},
        )
    except HTTPException:
        raise
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
        user_path = get_user_storage_path(current_user.id)

        # 确保文件名安全
        safe_filename = Path(filename).name
        file_path = user_path / safe_filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

        # 删除文件
        file_path.unlink()

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
        user_path = get_user_storage_path(current_user.id)

        # 删除所有文件
        file_count = 0
        for file_path in user_path.iterdir():
            if file_path.is_file():
                file_path.unlink()
                file_count += 1

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
