import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _find_npm() -> str | None:
    """查找 npm 可执行文件路径"""
    system = platform.system()
    
    # 首先尝试在 PATH 中查找
    npm_cmd = "npm.cmd" if system == "Windows" else "npm"
    npm_path = shutil.which(npm_cmd)
    if npm_path:
        return npm_path
    
    # Windows 常见安装路径
    if system == "Windows":
        common_paths = [
            r"C:\Program Files\nodejs\npm.cmd",
            r"C:\Program Files (x86)\nodejs\npm.cmd",
            r"D:\codesoftware\nodejs\npm.cmd",
            r"D:\codesoftware\nodejs_v24\npm.cmd",
        ]
        # 从环境变量 PATH 中提取路径
        for path in os.environ.get("PATH", "").split(os.pathsep):
            npm_exe = Path(path) / "npm.cmd"
            if npm_exe.exists():
                return str(npm_exe)
        # 检查常见路径
        for path in common_paths:
            if Path(path).exists():
                return path
    
    return None


def _pids_listening_on_port(port: int) -> list[int]:
    system = platform.system()
    pids: list[int] = []
    
    if system == "Windows":
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in (proc.stdout or "").strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                try:
                    pids.append(int(parts[4]))
                except ValueError:
                    continue
    else:
        proc = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        for part in (proc.stdout or "").strip().split():
            try:
                pids.append(int(part))
            except ValueError:
                continue
    return sorted(set(pids))


def _kill_pid(pid: int, timeout_s: float = 2.0) -> None:
    system = platform.system()
    
    if system == "Windows":
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T"], capture_output=True, check=False)
        except Exception:
            pass
        
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if not _is_pid_alive(pid):
                return
            time.sleep(0.05)
        
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], capture_output=True, check=False)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except PermissionError:
            return

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)

        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except PermissionError:
            return


def _is_pid_alive(pid: int) -> bool:
    system = platform.system()
    if system == "Windows":
        proc = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in proc.stdout
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False


def free_port(port: int) -> None:
    pids = _pids_listening_on_port(port)
    if not pids:
        return
    for pid in pids:
        _kill_pid(pid)


def main() -> int:
    backend_port = 8001
    frontend_port = 5173

    free_port(backend_port)
    free_port(frontend_port)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(backend_port),
        "--reload",
    ]

    backend_proc = subprocess.Popen(backend_cmd, cwd=str(PROJECT_ROOT))
    
    # 查找 npm 路径
    npm_path = _find_npm()
    
    frontend_proc = None
    if npm_path:
        frontend_cmd = [
            npm_path,
            "run",
            "dev",
            "--",
            "--host",
            "0.0.0.0",
            "--port",
            str(frontend_port),
        ]
        try:
            frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(FRONTEND_DIR))
            print(f"\n✅ 前端服务启动成功: http://localhost:{frontend_port}")
        except Exception as e:
            print(f"\n⚠️  前端启动失败: {e}")
    else:
        print("\n" + "=" * 60)
        print("⚠️  警告: 未找到 npm，跳过前端启动")
        print("   请安装 Node.js 以运行前端开发服务器")
        print(f"   后端服务仍在运行: http://0.0.0.0:{backend_port}")
        print("=" * 60 + "\n")

    try:
        while True:
            backend_rc = backend_proc.poll()
            if frontend_proc:
                frontend_rc = frontend_proc.poll()
                if backend_rc is not None:
                    if frontend_proc.poll() is None:
                        frontend_proc.terminate()
                    return backend_rc
                if frontend_rc is not None:
                    if backend_proc.poll() is None:
                        backend_proc.terminate()
                    return frontend_rc
            else:
                if backend_rc is not None:
                    return backend_rc
            time.sleep(0.2)
    except KeyboardInterrupt:
        procs = [p for p in (frontend_proc, backend_proc) if p]
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=3)
            except Exception:
                if proc.poll() is None:
                    proc.kill()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

