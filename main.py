#!/usr/bin/env python3
"""
启动脚本 - 同时启动前端和后端服务
适用于 Ubuntu/Linux 系统
"""

import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List

# 动态导入，避免全局依赖
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


class StartupError(RuntimeError):
    """启动错误异常"""
    pass


def ensure_command_exists(command_name: str) -> None:
    """检查命令是否存在"""
    if shutil.which(command_name) is None:
        raise StartupError(f"未找到命令: {command_name}")


def start_backend() -> subprocess.Popen:
    """启动后端服务"""
    try:
        # 动态导入，避免在启动时就需要所有依赖
        sys.path.insert(0, str(ROOT_DIR))
        from backend.common.config.config_service import ConfigService
        from backend.common.logger import get_logger
        
        logger = get_logger("startup_backend")
        
        # 检查配置
        ConfigService().get_config("llm_api")
        logger.info("LLM 配置加载成功")
    except Exception as exc:
        raise StartupError(f"后端初始化失败: {exc}") from exc
    
    # 启动后端服务
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.mainsystem.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "info",  # 减少日志输出
        ],
        cwd=ROOT_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,   # 合并错误输出
        start_new_session=True,     # 创建新会话组
    )


def start_frontend() -> subprocess.Popen:
    """启动前端服务"""
    ensure_command_exists("npm")
    
    # 检查前端目录是否存在
    if not FRONTEND_DIR.exists():
        raise StartupError(f"前端目录不存在: {FRONTEND_DIR}")
    
    # 检查 package.json
    package_json = FRONTEND_DIR / "package.json"
    if not package_json.exists():
        raise StartupError(f"未找到 package.json: {package_json}")
    
    return subprocess.Popen(
        [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
        ],
        cwd=FRONTEND_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,   # 合并错误输出
        start_new_session=True,      # 创建新会话组
    )


def terminate_processes(processes: List[subprocess.Popen]) -> None:
    """终止所有子进程（Linux/macOS版本）"""
    for process in processes:
        if process and process.poll() is None:  # 进程还在运行
            try:
                # 终止整个进程组
                pid = process.pid
                if pid > 0:
                    try:
                        # 尝试优雅终止
                        os.killpg(os.getpgid(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            except (AttributeError, OSError) as e:
                print(f"终止进程时出错: {e}")
    
    # 等待进程结束
    wait_time = 3
    for _ in range(wait_time * 2):  # 每0.5秒检查一次
        all_stopped = True
        for process in processes:
            if process and process.poll() is None:
                all_stopped = False
                break
        
        if all_stopped:
            break
        time.sleep(0.5)
    
    # 强制终止未响应的进程
    for process in processes:
        if process and process.poll() is None:
            try:
                pid = process.pid
                if pid > 0:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            finally:
                try:
                    process.terminate()
                except Exception:
                    pass
    
    # 清理进程对象
    for process in processes:
        if process:
            try:
                process.wait(timeout=1)
            except (subprocess.TimeoutExpired, Exception):
                pass


def check_ports() -> None:
    """检查端口是否被占用"""
    import socket
    
    ports_to_check = [
        (8000, "后端"),
        (8080, "前端"),
    ]
    
    busy_ports = []
    for port, service_name in ports_to_check:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:  # 端口已被占用
                busy_ports.append((port, service_name))
        except Exception:
            pass
        finally:
            if sock:
                sock.close()
    
    if busy_ports:
        print("警告: 以下端口已被占用:")
        for port, service_name in busy_ports:
            print(f"  {service_name}端口 {port}")
        
        response = input("是否继续启动？(y/N): ").strip().lower()
        if response != 'y':
            raise StartupError("端口被占用，启动终止")


def print_service_info() -> None:
    """打印服务信息"""
    print("=" * 50)
    print("服务启动信息:")
    print(f"  后端: http://localhost:8000")
    print(f"  前端: http://localhost:8080")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")
    print("=" * 50)


def main() -> int:
    """主函数"""
    global os
    import os
    
    # 打印启动信息
    print(f"启动目录: {ROOT_DIR}")
    print(f"当前Python: {sys.executable}")
    print()
    
    processes: List[subprocess.Popen] = []
    
    try:
        # 检查端口
        check_ports()
        
        # 启动后端
        print("启动后端服务...")
        backend_process = start_backend()
        processes.append(backend_process)
        
        # 等待后端启动
        print("等待后端服务启动...")
        for i in range(10):  # 最多等待10秒
            if backend_process.poll() is not None:
                raise StartupError("后端服务启动失败")
            
            # 检查后端是否在监听端口
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('127.0.0.1', 8000))
                sock.close()
                if result == 0:
                    print("后端服务启动成功")
                    break
            except Exception:
                pass
            
            if i < 9:  # 前9次等待
                time.sleep(1)
        else:
            raise StartupError("后端服务启动超时")
        
        # 启动前端
        print("启动前端服务...")
        frontend_process = start_frontend()
        processes.append(frontend_process)
        
        # 等待前端启动
        print("等待前端服务启动...")
        time.sleep(3)  # 给前端一些启动时间
        if frontend_process.poll() is not None:
            raise StartupError("前端服务启动失败")
        
        print("前端服务启动成功")
        print()
        
        # 打印服务信息
        print_service_info()
        
        # 设置信号处理
        def signal_handler(signum, frame):
            print(f"\n收到信号 {signum}，正在关闭服务...")
            terminate_processes(processes)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 主循环 - 只监控进程状态
        while True:
            time.sleep(1)
            
            # 检查所有进程
            for idx, process in enumerate(processes):
                if process.poll() is not None:
                    service_name = "后端" if idx == 0 else "前端"
                    print(f"\n{service_name}服务异常退出")
                    terminate_processes(processes)
                    return 1
            
            # 可选：定期检查服务是否可用
            # 这里可以添加健康检查，但为了简单起见，只监控进程状态
    
    except StartupError as exc:
        print(f"启动失败: {exc}")
        terminate_processes(processes)
        return 1
    
    except KeyboardInterrupt:
        print("\n用户中断，正在关闭服务...")
        terminate_processes(processes)
        return 0
    
    except Exception as exc:
        print(f"发生未预期错误: {exc}")
        import traceback
        traceback.print_exc()
        terminate_processes(processes)
        return 1


if __name__ == "__main__":
    sys.exit(main())