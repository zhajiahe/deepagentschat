"""
文件管理 API 路由

提供文件上传、下载、列表等功能
使用本地文件系统存储（简化版本，不依赖自定义 backend）
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
        user_path = get_user_storage_path(current_user.id)

        # 清理子目录路径，防止路径遍历
        if subdir:
            subdir = subdir.replace("../", "").replace("..\\", "").strip("/")
            target_path = (user_path / subdir).resolve()
            # 确保目标路径在用户目录内
            if not str(target_path).startswith(str(user_path.resolve())):
                raise HTTPException(status_code=403, detail="无效的目录路径")
        else:
            target_path = user_path

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"目录不存在: {subdir}")

        files = []
        for item_path in sorted(target_path.iterdir()):
            # 计算相对路径
            rel_path = str(item_path.relative_to(user_path))

            if item_path.is_dir():
                # 目录
                files.append(
                    FileInfo(
                        filename=item_path.name,
                        size=0,
                        path=rel_path,
                        is_dir=True,
                    )
                )
            elif item_path.is_file():
                # 文件
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
        user_path = get_user_storage_path(current_user.id)

        # 清理路径，防止路径遍历
        safe_path = file_path.replace("../", "").replace("..\\", "")
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
        user_path = get_user_storage_path(current_user.id)

        # 清理路径，防止路径遍历
        safe_path = file_path.replace("../", "").replace("..\\", "")
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

        return BaseResponse(
            success=True,
            code=200,
            msg="读取文件成功",
            data={"filename": Path(file_path).name, "content": content},
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
        user_path = get_user_storage_path(current_user.id)

        # 清理路径，防止路径遍历
        safe_path = file_path.replace("../", "").replace("..\\", "")
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
            import shutil

            shutil.rmtree(full_path)
        else:
            raise HTTPException(status_code=400, detail="无效的文件类型")

        logger.info(f"User {current_user.id} deleted: {file_path}")

        return BaseResponse(
            success=True,
            code=200,
            msg="删除成功",
            data={"filename": Path(file_path).name, "message": f"{Path(file_path).name} 已删除"},
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
