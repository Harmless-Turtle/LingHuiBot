"""NoneBot 启动冒烟测试（Pytest 版本）。"""

import os
import queue
import subprocess
import sys
import threading
import time


def test_nonebot_startup_smoke():
    """验证 NoneBot 核心与已配置插件能否正常加载并完成启动。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # 若 CI 或新环境缺少 .env 文件，注入必要的基础配置确保插件顺利加载
    env.setdefault("LOCALSTORE_USE_CWD", "true")

    start_time = time.time()
    timeout_seconds = 60
    success = False
    captured_logs: list[str] = []

    # 启动 NoneBot ASGI 服务子进程
    process = subprocess.Popen(
        ["uv", "run", "nb", "run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    log_queue: queue.Queue[str] = queue.Queue()

    def reader():
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                log_queue.put(line)
            process.stdout.close()

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    try:
        while time.time() - start_time < timeout_seconds:
            try:
                line = log_queue.get(timeout=0.5)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue

            captured_logs.append(line)
            # 兼容实时控制台输出（避免 Windows GBK 终端字符集异常）
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except Exception:
                sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))
                sys.stdout.buffer.flush()

            # 检测到启动完成标记
            if "Application startup complete" in line:
                success = True
                break
    finally:
        # 测试结束，强制回收常驻进程，避免占用端口
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    error_summary = "".join(captured_logs[-30:])
    assert success, (
        f"NoneBot 启动冒烟测试失败：未在 {timeout_seconds} 秒内检测到 'Application startup complete'。\n"
        f"最近的启动日志如下：\n{error_summary}"
    )
