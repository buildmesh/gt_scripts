#!/usr/bin/env python3
"""Poll Gas Town rigs and nudge witness/refinery services."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
from datetime import datetime

LOOP_INTERVAL_SECONDS = 2 * 60


def run_json_command(command: list[str], label: str):
    """Run a command that returns JSON and parse its stdout."""
    log_command(command)
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        print(f"[{timestamp()}] {label} failed: {stderr or exc}")
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"[{timestamp()}] {label} returned invalid JSON: {exc}")
        return None


def run_command(command: list[str], label: str) -> bool:
    """Run a command and report failures."""
    log_command(command)
    try:
        subprocess.run(command, check=True, text=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        print(f"[{timestamp()}] {label} failed: {stderr or exc}")
        return False


def run_text_command(command: list[str], label: str):
    """Run a command and return raw stdout text."""
    log_command(command)
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        print(f"[{timestamp()}] {label} failed: {stderr or exc}")
        return None


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_command(command: list[str]) -> None:
    print(f"[{timestamp()}] {shlex.join(command)}")


def has_done_polecat(rig_status_output: str) -> bool:
    """Check the Polecats section for any entry marked as done."""
    in_polecats_section = False

    for line in rig_status_output.splitlines():
        if not in_polecats_section:
            if line.strip().startswith("Polecats"):
                in_polecats_section = True
            continue

        # Next top-level heading means Polecats section ended.
        if line and not line[0].isspace():
            break

        if re.search(r":\s*done\b", line):
            return True

    return False


def loop_once(iteration: int) -> None:
    rigs = run_json_command(["gt", "rig", "list", "--json"], "gt rig list --json")
    if rigs is None:
        return

    for rig in rigs:
        if rig.get("status") != "operational":
            continue

        rig_name = rig.get("name")
        if not rig_name:
            continue

        idle_polecats = False
        rig_status_output = run_text_command(
            ["gt", "rig", "status", rig_name],
            f"gt rig status {rig_name}",
        )
        if rig_status_output is not None:
            idle_polecats = has_done_polecat(rig_status_output)

        if idle_polecats:
            run_command(
                [
                    "gt",
                    "nudge",
                    f"{rig_name}/witness",
                    "-m",
                    "Please check on stale polecats and 'gt done' them",
                ],
                f"nudge witness for {rig_name}",
            )

        if iteration % 5 == 0:
            print(f"[{timestamp()}] periodic witness health check triggered for {rig_name}")
            run_command(
                [
                    "gt",
                    "nudge",
                    f"{rig_name}/witness",
                    "-m",
                    "Please check on all working polecats and make sure they aren't stuck or nonresponsive",
                ],
                f"periodic witness health nudge for {rig_name}",
            )

        mq = run_json_command(
            ["gt", "mq", "list", rig_name, "--json"],
            f"gt mq list {rig_name} --json",
        )
        if mq:
            run_command(
                ["gt", "nudge", f"{rig_name}/refinery", "-m", "Please process merge queue. Merge conflicts should result in a bead to resolve the merge conflict"],
                f"nudge refinery for {rig_name}",
            )


def main() -> None:
    print(f"[{timestamp()}] Starting rig watcher. Press CTRL-C to stop.")
    iteration = 0
    try:
        while True:
            iteration += 1
            loop_once(iteration)
            time.sleep(LOOP_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Stopping rig watcher.")


if __name__ == "__main__":
    main()
