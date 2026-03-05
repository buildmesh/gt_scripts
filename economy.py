#!/usr/bin/env python3
"""Economy mode: periodically stop witness tmux session and deacon service."""

from __future__ import annotations

import shlex
import subprocess
import time
from datetime import datetime

LOOP_INTERVAL_SECONDS = 15


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_command(command: list[str]) -> None:
    print(f"[{timestamp()}] {shlex.join(command)}")


def run_command(command: list[str], label: str, check: bool = True) -> bool:
    """Run a command, optionally ignoring failures."""
    log_command(command)
    try:
        subprocess.run(command, check=check, text=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        print(f"[{timestamp()}] {label} failed: {stderr or exc}")
        return False


def loop_once() -> None:
    run_command(
        ["tmux", "kill-session", "-t", "gt-witness"],
        "kill fm-witness tmux session",
        check=False,
    )
    run_command(["gt", "deacon", "stop"], "gt deacon stop")


def main() -> None:
    print(f"[{timestamp()}] Starting economy mode. Press CTRL-C to stop.")
    try:
        while True:
            loop_once()
            time.sleep(LOOP_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Stopping economy mode.")


if __name__ == "__main__":
    main()
