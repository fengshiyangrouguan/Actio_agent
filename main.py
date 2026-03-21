import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from backend.common.config.config_service import ConfigService
from backend.common.logger import get_logger


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
logger = get_logger("start_up")


class StartupError(RuntimeError):
    pass


def ensure_command_exists(command_name: str) -> None:
    """检查命令是否存在"""
    if shutil.which(command_name) is None:
        raise StartupError(f"未找到启动命令: {command_name}")


def start_backend() -> subprocess.Popen:
    """启动后端服务"""
    # 根据平台选择不同的创建标志
    creation_flags = 0
    if sys.platform.startswith("win"):
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
    
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
        ],
        cwd=ROOT_DIR,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creation_flags,
        # Linux/macOS 使用进程组
        preexec_fn=os.setsid if not sys.platform.startswith("win") else None,
    )


def start_frontend() -> subprocess.Popen:
    """启动前端服务"""
    npm_command = "npm.cmd" if sys.platform.startswith("win") else "npm"
    ensure_command_exists(npm_command)
    
    creation_flags = 0
    if sys.platform.startswith("win"):
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
    
    return subprocess.Popen(
        [
            npm_command,
            "run",
            "dev",
            "--",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
        ],
        cwd=FRONTEND_DIR,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creation_flags,
        preexec_fn=os.setsid if not sys.platform.startswith("win") else None,
    )


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    """终止所有子进程（跨平台）"""
    for process in processes:
        if process.poll() is None:
            try:
                if sys.platform.startswith("win"):
                    # Windows: 发送 CTRL_BREAK_EVENT
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # Linux/macOS: 终止整个进程组
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except (ProcessLookupError, AttributeError, OSError):
                try:
                    process.terminate()
                except Exception:
                    pass
    
    # 等待进程结束
    time.sleep(2)
    
    # 强制终止未响应的进程
    for process in processes:
        if process.poll() is None:
            try:
                if sys.platform.startswith("win"):
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass


def check_ports() -> None:
    """检查端口是否被占用"""
    import socket
    
    ports = [8000, 8080]
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            logger.warning(f"端口 {port} 已被占用")
            response = input(f"端口 {port} 已被占用，是否继续？(y/N): ")
            if response.lower() != 'y':
                raise StartupError(f"端口 {port} 被占用，启动终止")
        sock.close()


def main() -> int:
    """主函数"""
    # 导入 os 模块（用于跨平台进程管理）
    global os
    import os
    
    try:
        # 检查配置文件
        ConfigService().get_config("llm_api")
        logger.info("LLM 配置加载成功")
    except Exception as exc:
        raise StartupError(f"LLM 配置加载失败: {exc}") from exc
    
    # 检查端口
    try:
        check_ports()
    except StartupError as exc:
        print(f"端口检查失败: {exc}")
        return 1
    
    processes: list[subprocess.Popen] = []
    
    try:
        # 启动后端
        backend_process = start_backend()
        processes.append(backend_process)
        logger.info("后端服务启动中...")
        
        # 等待后端启动
        time.sleep(2)
        if backend_process.poll() is not None:
            stdout, stderr = backend_process.communicate()
            raise StartupError(f"后端启动失败: {stderr}")
        
        # 启动前端
        frontend_process = start_frontend()
        processes.append(frontend_process)
        logger.info("前端服务启动中...")
        
        # 信号处理
        def handle_signal(signum: int, frame: object) -> None:
            print(f"\n收到信号 {signum}，正在关闭服务...")
            terminate_processes(processes)
            raise SystemExit(0)
        
        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_signal)
        
        # 监控子进程
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    stdout, stderr = process.communicate()
                    if stderr:
                        print(f"子进程错误输出: {stderr}")
                    print(f"子进程已退出，退出码: {exit_code}")
                    terminate_processes(processes)
                    return exit_code
            time.sleep(1)
            
    except StartupError as exc:
        print(f"启动失败: {exc}")
        terminate_processes(processes)
        return 1
    except SystemExit:
        return 0
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭服务...")
        terminate_processes(processes)
        return 0
    except Exception as exc:
        print(f"发生未预期错误: {exc}")
        import traceback
        traceback.print_exc()
        terminate_processes(processes)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())