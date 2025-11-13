.PHONY: help install dev test lint format clean db-init db-migrate db-upgrade

# 默认目标
.DEFAULT_GOAL := help

help: ## 显示帮助信息
	@echo "FastAPI Template - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## 安装依赖
	@echo "📦 安装依赖..."
	uv sync

dev: ## 启动开发服务器
	@echo "🚀 启动开发服务器..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## 运行测试
	@echo "🧪 运行测试..."
	uv run pytest tests/ -v

lint: ## 代码检查
	@echo "🔍 代码检查..."
	uv run ruff check app/ tests/

lint-fix: ## 代码检查并修复
	@echo "🔧 代码检查并修复..."
	uv run ruff check app/ tests/ --fix

format: ## 格式化代码
	@echo "🎨 格式化代码..."
	uv run ruff format app/ tests/

type-check: ## 类型检查
	@echo "🔍 类型检查..."
	uv run mypy app/

db-migrate: ## 创建数据库迁移 (make db-migrate msg="xxx")
	@if [ -z "$(msg)" ]; then echo "❌ 需要提供消息: make db-migrate msg=\"描述\""; exit 1; fi
	uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## 升级数据库
	@echo "⬆️  升级数据库..."
	uv run alembic upgrade head

db-downgrade: ## 降级数据库
	@echo "⬇️  降级数据库..."
	uv run alembic downgrade -1

clean: ## 清理临时文件
	@echo "🧹 清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
