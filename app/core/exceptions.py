"""
统一异常处理模块

提供自定义异常类和全局异常处理器，实现统一的错误响应格式
"""

from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.models.base import BaseResponse


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """参数验证异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code=1001,
            message=message,
            status_code=400,
            details=details,
        )


class AuthenticationException(AppException):
    """认证异常"""

    def __init__(self, message: str = "认证失败，请重新登录", details: dict[str, Any] | None = None):
        super().__init__(
            code=1002,
            message=message,
            status_code=401,
            details=details,
        )


class AuthorizationException(AppException):
    """权限异常"""

    def __init__(self, message: str = "权限不足", details: dict[str, Any] | None = None):
        super().__init__(
            code=1003,
            message=message,
            status_code=403,
            details=details,
        )


class ResourceNotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, resource: str, details: dict[str, Any] | None = None):
        super().__init__(
            code=1004,
            message=f"{resource}不存在",
            status_code=404,
            details=details,
        )


class ResourceConflictException(AppException):
    """资源冲突异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code=1005,
            message=message,
            status_code=409,
            details=details,
        )


class ClientClosedException(AppException):
    """客户端关闭连接异常"""

    def __init__(self, message: str = "客户端已关闭连接", details: dict[str, Any] | None = None):
        super().__init__(
            code=1008,
            message=message,
            status_code=499,
            details=details,
        )


class BusinessLogicException(AppException):
    """业务逻辑异常"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code=1006,
            message=message,
            status_code=400,
            details=details,
        )


class InternalServerException(AppException):
    """服务器内部异常"""

    def __init__(self, message: str = "服务器内部错误", details: dict[str, Any] | None = None):
        super().__init__(
            code=1007,
            message=message,
            status_code=500,
            details=details,
        )


def create_error_response(
    status_code: int,
    code: int,
    message: str,
    details: dict[str, Any] | None = None,
) -> Response:
    """创建统一的错误响应"""
    return JSONResponse(
        status_code=status_code,
        content=BaseResponse(
            success=False,
            code=code,
            msg=message,
            err=details,
        ).model_dump(),
    )


async def app_exception_handler(request: Request, exc: Exception) -> Response:
    """应用异常处理器"""
    if not isinstance(exc, AppException):
        # 如果不是AppException，转给通用处理器
        return await general_exception_handler(request, exc)

    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    """HTTP异常处理器"""
    if not isinstance(exc, HTTPException):
        # 如果不是HTTPException，转给通用处理器
        return await general_exception_handler(request, exc)

    # 映射HTTP状态码到错误码
    error_code_map = {
        400: 2001,  # Bad Request
        401: 2002,  # Unauthorized
        403: 2003,  # Forbidden
        404: 2004,  # Not Found
        409: 2005,  # Conflict
        422: 2006,  # Unprocessable Entity
        500: 2007,  # Internal Server Error
    }

    code = error_code_map.get(exc.status_code, 2000)
    return create_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
        details=getattr(exc, "details", None),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """Pydantic验证异常处理器"""
    if hasattr(exc, "errors") and hasattr(exc, "body"):
        # Pydantic ValidationError
        error_details = []
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            error_details.append(
                {
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return create_error_response(
            status_code=422,
            code=2006,
            message="请求参数验证失败",
            details={"validation_errors": error_details},
        )

    # 其他验证异常
    return create_error_response(
        status_code=400,
        code=2001,
        message=str(exc),
    )


async def general_exception_handler(request: Request, exc: Exception) -> Response:
    """通用异常处理器"""
    # 记录错误日志
    from loguru import logger

    logger.exception(f"Unhandled exception: {exc}")

    return create_error_response(
        status_code=500,
        code=2007,
        message="服务器内部错误",
        details={"error_type": type(exc).__name__},
    )


# 便捷函数用于抛出常用异常
def raise_validation_error(message: str, details: dict[str, Any] | None = None) -> None:
    """抛出参数验证异常"""
    raise ValidationException(message, details)


def raise_auth_error(message: str = "认证失败，请重新登录", details: dict[str, Any] | None = None) -> None:
    """抛出认证异常"""
    raise AuthenticationException(message, details)


def raise_permission_error(message: str = "权限不足", details: dict[str, Any] | None = None) -> None:
    """抛出权限异常"""
    raise AuthorizationException(message, details)


def raise_not_found_error(resource: str, details: dict[str, Any] | None = None) -> None:
    """抛出资源不存在异常"""
    raise ResourceNotFoundException(resource, details)


def raise_conflict_error(message: str, details: dict[str, Any] | None = None) -> None:
    """抛出资源冲突异常"""
    raise ResourceConflictException(message, details)


def raise_client_closed_error(message: str = "客户端已关闭连接", details: dict[str, Any] | None = None) -> None:
    """抛出客户端关闭连接异常"""
    raise ClientClosedException(message, details)


def raise_business_error(message: str, details: dict[str, Any] | None = None) -> None:
    """抛出业务逻辑异常"""
    raise BusinessLogicException(message, details)


def raise_internal_error(message: str = "服务器内部错误", details: dict[str, Any] | None = None) -> None:
    """抛出服务器内部异常"""
    raise InternalServerException(message, details)
