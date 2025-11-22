"""
存储配置和工具函数

统一管理文件存储路径和相关工具函数，供 tools.py、tools_docker.py 和 files.py 使用
"""

import uuid
from pathlib import Path

# 文件存储根目录
STORAGE_ROOT = Path("/tmp/user_files")
PUBLIC_DIR = STORAGE_ROOT / "public"  # 公共目录
TOOLS_VENV_DIR = STORAGE_ROOT / ".tools_venv"  # 工具专用虚拟环境（仅 tools.py 使用）

# 确保目录存在
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def get_user_storage_path(user_id: str | uuid.UUID) -> Path:
    """
    获取用户的存储目录

    Args:
        user_id: 用户 ID（字符串或 UUID）

    Returns:
        Path: 用户存储目录路径
    """
    user_path = STORAGE_ROOT / str(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path


def get_work_path(user_id: str | None = None) -> Path:
    """
    获取工作目录

    Args:
        user_id: 用户 ID（可选），如果为 None 则返回公共目录

    Returns:
        Path: 工作目录路径
    """
    if user_id:
        return get_user_storage_path(user_id)
    return PUBLIC_DIR


def sanitize_path(user_id: str | None, filename: str) -> Path:
    """
    验证并规范化文件路径，防止路径遍历攻击

    Args:
        user_id: 用户 ID（可选）
        filename: 文件名或相对路径

    Returns:
        Path: 规范化后的完整路径

    Raises:
        ValueError: 如果路径包含非法字符或尝试访问父目录
    """
    work_path = get_work_path(user_id)

    # 移除路径中的 ../ 和绝对路径
    filename = filename.lstrip("/")
    if ".." in Path(filename).parts:
        raise ValueError("路径不能包含 '..'")

    file_path = (work_path / filename).resolve()

    # 确保文件路径在工作目录内
    if not str(file_path).startswith(str(work_path.resolve())):
        raise ValueError("路径必须在工作目录内")

    return file_path


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除路径分隔符和其他不安全字符

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名
    """
    # 只保留文件名部分，移除路径
    safe_name = Path(filename).name

    # 替换不安全字符
    unsafe_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, "_")

    return safe_name or "unnamed"
