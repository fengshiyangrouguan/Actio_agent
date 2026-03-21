#!/bin/bash
# start.sh - Linux 启动脚本

set -e

echo "Actio Agent 启动脚本 (Linux)"

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ "$PYTHON_VERSION" < "3.10" ]]; then
    echo "错误: 需要 Python 3.10 或更高版本"
    exit 1
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖
echo "检查 Python 依赖..."
pip list | grep -q fastapi || {
    echo "安装 Python 依赖..."
    pip install -r requirements.txt
}

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "安装前端依赖..."
    cd frontend && npm install && cd ..
fi