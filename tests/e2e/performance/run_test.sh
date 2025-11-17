#!/bin/bash

# 性能测试快速启动脚本

set -e

echo "======================================"
echo "🚀 FastAPI 性能测试"
echo "======================================"
echo ""

# 检查应用是否运行
check_app() {
    echo "检查应用状态..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 应用正在运行"
        return 0
    else
        echo "❌ 应用未运行"
        return 1
    fi
}

# 选择测试方法
echo "请选择测试方法:"
echo "1) Locust Web UI (推荐)"
echo "2) Locust 命令行模式"
echo "3) Python 性能分析脚本"
echo ""
read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        echo ""
        echo "启动 Locust Web UI..."
        echo "访问 http://localhost:8089 查看测试界面"
        echo ""
        locust -f locustfile.py --config locust.conf
        ;;
    2)
        echo ""
        echo "运行 Locust 命令行测试..."
        locust -f locustfile.py \
            --host=http://localhost:8000 \
            --users=5 \
            --spawn-rate=1 \
            --run-time=30s \
            --headless \
            --html=report_$(date +%Y%m%d_%H%M%S).html
        ;;
    3)
        echo ""
        echo "运行 Python 性能分析脚本..."
        python analyze_performance.py
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "✅ 测试完成"
echo "======================================"
