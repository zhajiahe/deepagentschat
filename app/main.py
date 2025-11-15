"""
FastAPI 应用主入口

提供应用配置、路由注册和中间件设置
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.users import auth_router
from app.api.users import router as users_router
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.lifespan import lifespan
from app.middleware.logging import LoggingMiddleware, setup_logging

# 设置日志
setup_logging()

# 创建 FastAPI 应用
app = FastAPI(
    title="API Doc",
    description="Langchain+fastapi生产级后端模板",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# 注册路由
@app.get("/", tags=["Root"])
async def root():
    """根路径，健康检查"""
    return {
        "status": "ok",
        "message": "Langchain+fastapi生产级后端 is running!",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """健康检查接口"""
    try:
        # 检查数据库
        from sqlalchemy import select

        from app.core.database import engine

        async with engine.begin() as conn:
            await conn.execute(select(1))

        # 检查 LangGraph
        from app.core.lifespan import get_compiled_graph

        get_compiled_graph()  # 验证图已初始化

        return {
            "status": "healthy",
            "database": "connected",
            "checkpointer": "connected",
            "langgraph": "ready",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# 注册认证路由
app.include_router(auth_router, prefix="/api/v1")

# 注册用户路由
app.include_router(users_router, prefix="/api/v1")

# 注册对话路由
app.include_router(chat_router, prefix="/api/v1")

# 注册会话管理路由
app.include_router(conversations_router, prefix="/api/v1")

# 挂载前端静态文件
web_dist_path = Path(__file__).parent.parent / "web" / "dist"
if web_dist_path.exists():
    # 挂载静态资源
    app.mount("/web/assets", StaticFiles(directory=str(web_dist_path / "assets")), name="web_assets")

    # SPA 路由处理 - 所有 /web/* 路径都返回 index.html
    @app.get("/web/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """处理 SPA 路由，所有路径都返回 index.html"""
        index_path = web_dist_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"detail": "Frontend not found"}

    logger.info(f"Frontend mounted at /web from {web_dist_path}")
else:
    logger.warning(f"Frontend dist directory not found at {web_dist_path}")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI application...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info",
    )
