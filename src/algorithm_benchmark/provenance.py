from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from importlib.metadata import PackageNotFoundError, version
from importlib import import_module
from typing import Any


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _gpu_provenance() -> tuple[str | None, int]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, 0
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name", "--format=csv,noheader"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        names = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        return (names[0] if names else None), len(names)
    except (OSError, subprocess.SubprocessError):
        return None, 0


def runtime_environment() -> dict[str, Any]:
    gpu_model, gpu_count = _gpu_provenance()
    cuda_available = False
    try:
        torch = import_module("torch")
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        cuda_available = False
    cpu_model = None
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as cpuinfo:
            for line in cpuinfo:
                if line.lower().startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        cpu_model = platform.processor() or None
    return {
        "hostname": socket.gethostname(),
        "environment_id": os.environ.get("CONDA_DEFAULT_ENV"),
        "os": platform.platform(),
        "cpu_model": cpu_model,
        "cpu_count": os.cpu_count(),
        "gpu_model": gpu_model,
        "gpu_count": gpu_count,
        "python_version": platform.python_version(),
        "sionna_version": _package_version("sionna"),
        "sionna_rt_version": _package_version("sionna-rt"),
        "torch_version": _package_version("torch"),
        "cuda_available": cuda_available,
    }
