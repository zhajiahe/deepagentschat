#!/bin/bash
# 构建 Docker 工具镜像

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 镜像名称
IMAGE_NAME="${DOCKER_IMAGE:-deepagentschat-tools:latest}"
DOCKERFILE="Dockerfile.tools"

# 检查参数
for arg in "$@"
do
    case $arg in
        -c|--cn)
        DOCKERFILE="Dockerfile.tools.cn"
        echo -e "${YELLOW}使用国内镜像源构建${NC}"
        shift
        ;;
    esac
done

echo -e "${GREEN}开始构建 Docker 工具镜像...${NC}"
echo -e "镜像名称: ${YELLOW}${IMAGE_NAME}${NC}"
echo -e "Dockerfile: ${YELLOW}${DOCKERFILE}${NC}"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker 服务是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误: Docker 服务未运行${NC}"
    echo "请启动 Docker 服务: sudo systemctl start docker"
    exit 1
fi

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"

echo -e "${GREEN}项目根目录: ${PROJECT_ROOT}${NC}"

# 构建镜像
echo -e "${GREEN}开始构建...${NC}"
docker build \
    -t "${IMAGE_NAME}" \
    -f "${SCRIPT_DIR}/${DOCKERFILE}" \
    "${PROJECT_ROOT}"

# 检查构建结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 镜像构建成功!${NC}"
    echo ""
    echo "镜像信息:"
    docker images "${IMAGE_NAME}"
    echo ""
    echo "测试镜像:"
    echo "  docker run --rm ${IMAGE_NAME} python -c 'import pandas; print(pandas.__version__)'"
else
    echo -e "${RED}❌ 镜像构建失败${NC}"
    exit 1
fi
