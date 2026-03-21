#!/bin/bash
# start.sh - 启动 Actio Agent 完整流程

set -e

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 错误处理函数
handle_error() {
    log_error "脚本执行失败，行号: $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

# 清理函数
cleanup() {
    log_info "收到退出信号，正在清理..."
    
    # 终止所有子进程
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        log_info "终止后端服务 (PID: $BACKEND_PID)"
        kill -TERM $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$LAUNCH_PID" ] && kill -0 $LAUNCH_PID 2>/dev/null; then
        log_info "终止 launch_nodes 进程 (PID: $LAUNCH_PID)"
        kill -TERM $LAUNCH_PID 2>/dev/null || true
        wait $LAUNCH_PID 2>/dev/null || true
    fi
    
    log_info "清理完成"
    exit 0
}

# 设置退出信号处理
trap cleanup INT TERM

# 检查是否以 root 权限运行（修改串口权限需要）
check_permissions() {
    if [ "$EUID" -ne 0 ]; then 
        log_warn "未以 root 权限运行，可能无法修改串口权限"
        log_warn "建议使用: sudo ./start.sh"
        echo ""
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 步骤1: 修改串口权限
setup_serial_ports() {
    log_step "步骤 1/4: 配置串口权限..."
    
    # 检查是否有串口设备
    if ls /dev/ttyUSB* 1>/dev/null 2>&1; then
        if [ "$EUID" -eq 0 ]; then
            log_info "修改串口设备权限..."
            sudo chmod 666 /dev/ttyUSB* 2>/dev/null || log_warn "无法修改串口权限"
            log_info "串口权限已设置为 666"
        else
            log_warn "跳过串口权限修改（需要 root 权限）"
            log_info "当前串口设备列表:"
            ls -la /dev/ttyUSB* 2>/dev/null || echo "未找到串口设备"
        fi
    else
        log_warn "未找到串口设备 /dev/ttyUSB*"
        log_info "请确保机械臂已连接并安装驱动"
    fi
    echo ""
}

# 步骤2: 查找端口
find_ports() {
    log_step "步骤 2/4: 查找机械臂端口..."
    
    # 检查脚本是否存在
    if [ ! -f "backend/dobot_xtrainer/scripts/1_find_port.py" ]; then
        log_error "找不到端口查找脚本: backend/dobot_xtrainer/scripts/1_find_port.py"
        return 1
    fi
    
    # 运行端口查找脚本
    log_info "运行端口查找脚本..."
    python3 backend/dobot_xtrainer/scripts/1_find_port.py
    
    if [ $? -eq 0 ]; then
        log_info "端口查找完成"
    else
        log_warn "端口查找失败，但继续执行"
    fi
    echo ""
}

# 步骤3: 启动 launch_nodes
start_launch_nodes() {
    log_step "步骤 3/4: 启动 launch_nodes 服务..."
    
    # 检查脚本是否存在
    if [ ! -f "backend/dobot_xtrainer/experiments/launch_nodes.py" ]; then
        log_error "找不到 launch_nodes 脚本: backend/dobot_xtrainer/experiments/launch_nodes.py"
        return 1
    fi

    # 启动 launch_nodes 后台进程
    log_info "启动 launch_nodes.py..."
    python3 backend/dobot_xtrainer/experiments/launch_nodes.py &
    LAUNCH_PID=$!
    
    log_info "launch_nodes 已启动 (PID: $LAUNCH_PID)"
    
    # 等待几秒确保启动成功
    sleep 3
    
    # 检查进程是否还在运行
    if kill -0 $LAUNCH_PID 2>/dev/null; then
        log_info "launch_nodes 运行正常"
    else
        log_error "launch_nodes 启动失败"
        return 1
    fi
    echo ""
}

# 步骤4: 启动主程序
start_main() {
    log_step "步骤 4/4: 启动 Actio Agent 主程序..."
    
    # 检查 main.py 是否存在
    if [ ! -f "main.py" ]; then
        log_error "找不到 main.py"
        return 1
    fi

    # 启动主程序
    log_info "启动 main.py..."
    python3 main.py &
    BACKEND_PID=$!
    
    log_info "主程序已启动 (PID: $BACKEND_PID)"
    echo ""
}

# 显示启动信息
show_info() {
    echo ""
    echo "============================================================"
    log_info "Actio Agent 启动完成！"
    echo "============================================================"
    echo "后端服务: http://127.0.0.1:8000"
    echo "前端服务: http://127.0.0.1:8080"
    echo "============================================================"
    echo "launch_nodes PID: $LAUNCH_PID"
    echo "主程序 PID: $BACKEND_PID"
    echo "============================================================"
    log_info "按 Ctrl+C 停止所有服务"
    echo ""
}

# 监控进程
monitor_processes() {
    log_info "开始监控进程..."
    
    while true; do
        # 检查 launch_nodes 是否还在运行
        if ! kill -0 $LAUNCH_PID 2>/dev/null; then
            log_error "launch_nodes 进程已退出"
            cleanup
            exit 1
        fi
        
        # 检查主程序是否还在运行
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            log_error "主程序进程已退出"
            cleanup
            exit 1
        fi
        
        sleep 2
    done
}

# 主函数
main() {
    log_info "开始启动 Actio Agent..."
    echo ""
    
    # 检查权限（不强制要求）
    check_permissions
    echo ""

    # 检查虚拟环境
    if [ -d "venv" ]; then
        log_info "激活虚拟环境..."
        source venv/bin/activate
    fi

    # 执行启动步骤
    setup_serial_ports
    find_ports
    start_launch_nodes
    start_main
    
    # 显示信息
    show_info
    
    # 监控进程
    monitor_processes
}

# 运行主函数
main