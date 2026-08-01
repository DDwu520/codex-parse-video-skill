#!/usr/bin/env python3
"""跨平台启动和终止 parse-video 子进程树。"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Any


def executable_command(executable: os.PathLike[str] | str, *args: str) -> list[str]:
    path = os.fspath(executable)
    if path.casefold().endswith(".py"):
        return [sys.executable, path, *args]
    return [path, *args]


def popen_group_options(platform_name: str) -> dict[str, Any]:
    if platform_name == "windows":
        return {
            "creationflags": getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
            )
        }
    return {"start_new_session": True}


def terminate_process_tree(
    process: subprocess.Popen[str],
    *,
    platform_name: str,
    grace_seconds: float = 2.0,
) -> None:
    if process.poll() is not None:
        return
    if platform_name == "windows":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            process.wait(timeout=grace_seconds)
            return
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=grace_seconds)
            return
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass


def run_process(
    command: list[str],
    *,
    env: dict[str, str],
    timeout: int,
    platform_name: str,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **popen_group_options(platform_name),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process_tree(process, platform_name=platform_name)
        process.communicate()
        raise
    except (KeyboardInterrupt, BaseException):
        terminate_process_tree(process, platform_name=platform_name)
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
