import argparse
import shutil
import signal
import subprocess
import sys
import time
import signal
import uvicorn
from pathlib import Path

from backend.common.config.config_service import ConfigService
from backend.common.logger import get_logger


ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
logger = get_logger("start_up")


# 自定义启动异常，用于统一处理启动阶段错误
class StartupError(RuntimeError):
    pass


def ensure_command_exists(command_name: str) -> None:
    """
    检查系统命令是否存在（例如 python / npm）
    """
    if shutil.which(command_name) is None:
        raise StartupError(f"未找到启动命令: {command_name}")


def start_backend() -> subprocess.Popen[str]:
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
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def start_frontend() -> subprocess.Popen[str]:
    npm_command = "npm.cmd" if sys.platform.startswith("win") else "npm"

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
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def terminate_processes(processes):
    for p in processes:
        if p.poll() is None:
            try:
                p.send_signal(signal.CTRL_BREAK_EVENT)  #优雅退出
            except Exception:
                p.kill()

    time.sleep(2)

    for p in processes:
        if p.poll() is None:
            p.kill()


def main() -> int:
    """
    - 解析命令行参数
    - 校验配置
    - 启动前后端服务
    - 监听子进程状态
    """
    
    # 检查 LLM 配置
    try:
        llm_config = ConfigService().get_config("llm_api")
    except Exception as e:    
        raise StartupError(f"无法通过配置服务加载 configs/llm_api_config.toml，请先检查该文件是否存在且格式正确。")
    processes: list[subprocess.Popen[str]] = []

    try:
        # 启动前后端
        backend_process = start_backend()
        processes.append(backend_process)
        logger.info("后端服务启动中: http://127.0.0.1:8000")
        frontend_process = start_frontend()
        processes.append(frontend_process)
        logger.info("前端服务启动中: http://127.0.0.1:8080")

        # 信号处理（Ctrl+C / kill）
        def handle_signal(signum: int, frame: object) -> None:
            print(f"\n收到信号 {signum}，正在关闭服务...")
            terminate_processes(processes)
            raise SystemExit(0)

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_signal)

        # 主循环：监控子进程
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    # 任一子进程退出 → 全部关闭
                    print(f"子进程已退出，退出码: {exit_code}")
                    terminate_processes(processes)
                    return exit_code
            time.sleep(1)

    except StartupError as exc:
        # 可预期错误（配置 / 依赖等）
        print(f"启动失败: {exc}")
        terminate_processes(processes)
        return 1

    except SystemExit:
        return 0

    except Exception as exc:
        print(f"未预期错误: {exc}")
        terminate_processes(processes)
        return 1


if __name__ == "__main__":
    # 程序入口
    raise SystemExit(main())