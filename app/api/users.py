"""
用户管理API路由

提供用户的CRUD操作和认证相关接口
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentSuperUser, CurrentUser, DBSession
from app.core.security import create_tokens, get_password_hash, verify_password
from app.models.base import BasePageQuery, BaseResponse, PageResponse, Token
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.user import PasswordChange, UserCreate, UserListQuery, UserResponse, UserUpdate
from app.schemas.user_settings import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


# ==================== 认证相关接口 ====================


@auth_router.post("/login", response_model=BaseResponse[Token])
async def login(
    username: str,
    password: str,
    db: DBSession,
):
    """
    用户登录

    Args:
        username: 用户名
        password: 密码
        db: 数据库会话

    Returns:
        Token: 访问令牌和刷新令牌
    """
    # 查找用户
    result = await db.execute(select(User).where(User.username == username, User.deleted == 0))
    user = result.scalar_one_or_none()

    # 验证用户和密码
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 创建 token（user_id 转为字符串）
    access_token, refresh_token = create_tokens({"user_id": str(user.id)})

    return BaseResponse(
        success=True,
        code=200,
        msg="登录成功",
        data=Token(
            id=user.id,
            nickname=user.nickname,
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@auth_router.post("/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: DBSession,
):
    """
    用户注册

    Args:
        user_data: 用户注册数据
        db: 数据库会话

    Returns:
        UserResponse: 创建的用户信息
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username, User.deleted == 0))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email, User.deleted == 0))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    # 创建用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        nickname=user_data.nickname,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,  # 注册时默认激活
        is_superuser=False,  # 注册时不能直接成为超级管理员
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return BaseResponse(
        success=True,
        code=201,
        msg="注册成功",
        data=UserResponse.model_validate(new_user),
    )


@auth_router.get("/me", response_model=BaseResponse[UserResponse])
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    获取当前登录用户信息

    Args:
        current_user: 当前用户

    Returns:
        UserResponse: 当前用户信息
    """
    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户信息成功",
        data=UserResponse.model_validate(current_user),
    )


@auth_router.put("/me", response_model=BaseResponse[UserResponse])
async def update_current_user(
    user_data: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    更新当前登录用户信息

    Args:
        user_data: 更新的用户数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        UserResponse: 更新后的用户信息
    """
    # 更新邮箱
    if user_data.email is not None:
        # 检查邮箱是否已被其他用户使用
        result = await db.execute(
            select(User).where(User.email == user_data.email, User.id != current_user.id, User.deleted == 0)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被使用")
        current_user.email = user_data.email

    # 更新昵称
    if user_data.nickname is not None:
        current_user.nickname = user_data.nickname

    await db.commit()
    await db.refresh(current_user)

    return BaseResponse(
        success=True,
        code=200,
        msg="更新用户信息成功",
        data=UserResponse.model_validate(current_user),
    )


@auth_router.post("/reset-password", response_model=BaseResponse[None])
async def change_password(
    password_data: PasswordChange,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    修改密码

    Args:
        password_data: 密码修改数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        BaseResponse: 操作结果
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    # 检查新旧密码是否相同
    if password_data.old_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同",
        )

    # 更新密码
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return BaseResponse(
        success=True,
        code=200,
        msg="密码修改成功",
        data=None,
    )


# ==================== 用户管理接口（需要超级管理员权限） ====================


@router.get("", response_model=BaseResponse[PageResponse[UserResponse]])
async def get_users(
    db: DBSession,
    _current_user: CurrentSuperUser,
    page_query: BasePageQuery = Depends(),
    query_params: UserListQuery = Depends(),
):
    """
    获取用户列表（分页）- 需要超级管理员权限

    Args:
        page_query: 分页参数（page_num, page_size）
        query_params: 查询参数（keyword, is_active, is_superuser）
        _current_user: 当前用户（仅用于权限验证）
        db: 数据库会话
    """
    # 构建查询条件
    query = select(User).where(User.deleted == 0)

    # 关键词搜索
    if query_params.keyword:
        keyword = query_params.keyword
        query = query.where(
            (User.username.like(f"%{keyword}%"))
            | (User.email.like(f"%{keyword}%"))
            | (User.nickname.like(f"%{keyword}%"))
        )

    # 激活状态过滤
    if query_params.is_active is not None:
        query = query.where(User.is_active == query_params.is_active)

    # 超级管理员过滤
    if query_params.is_superuser is not None:
        query = query.where(User.is_superuser == query_params.is_superuser)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(User.create_time.desc()).limit(page_query.limit).offset(page_query.offset)

    result = await db.execute(query)
    users = result.scalars().all()

    # 转换为响应模型
    user_list = [UserResponse.model_validate(user) for user in users]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=user_list,
        ),
    )


# ==================== 用户设置接口（必须在 /{user_id} 之前） ====================


@router.get("/settings", response_model=BaseResponse[UserSettingsResponse])
async def get_user_settings(current_user: CurrentUser, db: DBSession):
    """
    获取用户设置

    Args:
        current_user: 当前用户
        db: 数据库会话

    Returns:
        UserSettingsResponse: 用户设置
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id, UserSettings.deleted == 0)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # 如果不存在，创建默认设置
        settings = UserSettings(
            user_id=current_user.id,
            theme="light",
            language="zh-CN",
            settings={},
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户设置成功",
        data=UserSettingsResponse(
            user_id=settings.user_id,
            default_model=settings.default_model,
            default_temperature=settings.default_temperature,
            default_max_tokens=settings.default_max_tokens,
            theme=settings.theme or "light",
            language=settings.language or "zh-CN",
            settings=settings.settings or {},
        ),
    )


@router.put("/settings", response_model=BaseResponse[UserSettingsResponse])
async def update_user_settings(settings_data: UserSettingsUpdate, current_user: CurrentUser, db: DBSession):
    """
    更新用户设置

    Args:
        settings_data: 用户设置更新数据
        current_user: 当前用户
        db: 数据库会话

    Returns:
        UserSettingsResponse: 更新后的用户设置
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id, UserSettings.deleted == 0)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # 如果不存在，创建新设置
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    # 更新字段
    update_data = settings_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(settings, key, value)

    await db.commit()
    await db.refresh(settings)

    return BaseResponse(
        success=True,
        code=200,
        msg="更新用户设置成功",
        data=UserSettingsResponse(
            user_id=settings.user_id,
            default_model=settings.default_model,
            default_temperature=settings.default_temperature,
            default_max_tokens=settings.default_max_tokens,
            theme=settings.theme or "light",
            language=settings.language or "zh-CN",
            settings=settings.settings or {},
        ),
    )


# ==================== 用户管理接口（需要超级管理员权限） ====================


@router.get("/{user_id}", response_model=BaseResponse[UserResponse])
async def get_user(
    user_id: uuid.UUID,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    获取单个用户详情 - 需要超级管理员权限

    Args:
        user_id: 用户ID
        _current_user: 当前用户（仅用于权限验证）
        db: 数据库会话
    """
    result = await db.execute(select(User).where(User.id == user_id, User.deleted == 0))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户成功",
        data=UserResponse.model_validate(user),
    )


@router.post("", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    创建新用户 - 需要超级管理员权限

    Args:
        user_data: 用户创建数据
        _current_user: 当前用户（仅用于权限验证）
        db: 数据库会话
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username, User.deleted == 0))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email, User.deleted == 0))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    # 创建用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        nickname=user_data.nickname,
        hashed_password=get_password_hash(user_data.password),
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return BaseResponse(
        success=True,
        code=201,
        msg="创建用户成功",
        data=UserResponse.model_validate(new_user),
    )


@router.put("/{user_id}", response_model=BaseResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    更新用户信息 - 需要超级管理员权限

    Args:
        user_id: 用户ID
        user_data: 用户更新数据
        _current_user: 当前用户（仅用于权限验证）
        db: 数据库会话
    """
    result = await db.execute(select(User).where(User.id == user_id, User.deleted == 0))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 更新字段
    if user_data.email is not None:
        # 检查邮箱是否已被其他用户使用
        result = await db.execute(
            select(User).where(User.email == user_data.email, User.id != user_id, User.deleted == 0)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被使用")
        user.email = user_data.email

    if user_data.nickname is not None:
        user.nickname = user_data.nickname

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    if user_data.is_superuser is not None:
        user.is_superuser = user_data.is_superuser

    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        success=True,
        code=200,
        msg="更新用户成功",
        data=UserResponse.model_validate(user),
    )


@router.delete("/{user_id}", response_model=BaseResponse[None])
async def delete_user(
    user_id: uuid.UUID,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    删除用户（逻辑删除）- 需要超级管理员权限

    Args:
        user_id: 用户ID
        _current_user: 当前用户（仅用于权限验证）
        db: 数据库会话
    """
    result = await db.execute(select(User).where(User.id == user_id, User.deleted == 0))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 逻辑删除
    user.deleted = 1
    await db.commit()

    return BaseResponse(success=True, code=200, msg="删除用户成功", data=None)
