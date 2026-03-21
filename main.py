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
    ensure_command_exists(npm_command)

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


def terminate_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                process.kill()

    time.sleep(2)

    for process in processes:
        if process.poll() is None:
            process.kill()


def main() -> int:
    try:
        ConfigService().get_config("llm_api")
    except Exception as exc:
        raise StartupError(str(exc)) from exc

    processes: list[subprocess.Popen[str]] = []

    try:
        backend_process = start_backend()
        processes.append(backend_process)
        logger.info("后端服务启动中: http://127.0.0.1:8000")

        frontend_process = start_frontend()
        processes.append(frontend_process)
        logger.info("前端服务启动中: http://127.0.0.1:8080")

        def handle_signal(signum: int, frame: object) -> None:
            print(f"\n收到信号 {signum}，正在关闭服务...")
            terminate_processes(processes)
            raise SystemExit(0)

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_signal)

        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
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
    except Exception as exc:
        print(f"发生未预期错误: {exc}")
        terminate_processes(processes)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
