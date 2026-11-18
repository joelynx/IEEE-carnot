"""Long-lived sandbox worker: one JSON request per stdin line, one JSON reply per line.

Each program runs in a fresh child process (runner.py) with a wall-clock
timeout and, on Linux, rlimits on CPU time, address space, file size and open
files.  The worker itself is started by the host inside an isolated
environment (WSL user+network namespace, or Docker with --network none).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "runner.py")

try:
    import resource
except ImportError:  # Windows "local" backend: timeout only
    resource = None


def _limits(cpu_seconds: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

    return apply


def run_one(code: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", RUNNER],
            input=json.dumps({"code": code}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            preexec_fn=_limits(int(timeout) + 1) if resource else None,
            cwd=HERE,
            env={"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "stage": "timeout", "error": f"program exceeded {timeout} s"}
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        tail = (completed.stderr or "").strip().splitlines()[-1:] or [f"exit code {completed.returncode}"]
        return {"ok": False, "stage": "crash", "error": tail[0][:300], "elapsed_ms": elapsed_ms}
    reply = json.loads(lines[-1])
    reply["elapsed_ms"] = elapsed_ms
    return reply


def main() -> None:
    sys.stdout.write(json.dumps({"ready": True, "python": sys.version.split()[0]}) + "\n")
    sys.stdout.flush()
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        reply = run_one(request["code"], float(request.get("timeout", 5)))
        reply["id"] = request.get("id")
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
