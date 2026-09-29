from __future__ import annotations

import json
import multiprocessing
import os
import signal
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStatus(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    TERMINATED = "terminated"
    STALE = "stale"


def _algorithm_worker(repo_root: str, run_id: str, cancel_event: Any) -> None:
    """Owned worker entrypoint. It deliberately imports the service in the child."""
    try:
        os.setsid()
    except OSError:
        pass
    from algorithm_packages import AlgorithmPackageService

    service = AlgorithmPackageService(Path(repo_root))
    service._execute_experiment(run_id, cancel_event=cancel_event)


class ExecutionManager:
    """Owns external worker processes and their lifecycle; never kills unrelated processes."""

    def __init__(self, repo_root: Path, runs_dir: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, tuple[multiprocessing.Process, Any]] = {}

    def _path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def _read(self, run_id: str) -> dict[str, Any]:
        return json.loads(self._path(run_id).read_text(encoding="utf-8"))

    def _write(self, record: dict[str, Any]) -> None:
        self._path(record["run_id"]).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    def start(self, run_id: str) -> dict[str, Any]:
        record = self._read(run_id)
        record.update({"status": RunStatus.STARTING.value, "stage": "STARTING", "worker_id": f"worker-{run_id}", "heartbeat_at": _now(), "cancel_requested": False, "gpu_cleanup_status": "NOT VERIFIED IN CURRENT ENVIRONMENT"})
        self._write(record)
        ctx = multiprocessing.get_context("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
        event = ctx.Event()
        process = ctx.Process(target=_algorithm_worker, args=(str(self.repo_root), run_id, event), name=f"glo-run-{run_id}")
        process.start()
        try:
            pgid = os.getpgid(process.pid)
        except OSError:
            pgid = None
        record.update({"status": RunStatus.RUNNING.value, "stage": "RUNNING", "pid": process.pid, "process_group_id": pgid, "started_at": record.get("started_at") or _now(), "heartbeat_at": _now()})
        self._write(record)
        self._handles[run_id] = (process, event)
        return record

    def request_cancel(self, run_id: str) -> dict[str, Any]:
        record = self._read(run_id)
        if record.get("status") not in {RunStatus.QUEUED.value, RunStatus.STARTING.value, RunStatus.RUNNING.value}:
            return record
        record.update({"status": RunStatus.CANCEL_REQUESTED.value, "stage": "CANCEL_REQUESTED", "cancel_requested": True, "cancel_requested_at": _now()})
        self._write(record)
        handle = self._handles.get(run_id)
        if handle:
            handle[1].set()
        return record

    def force_terminate(self, run_id: str, confirmation: str) -> dict[str, Any]:
        if confirmation != "FORCE_TERMINATE":
            raise ValueError("FORCE_TERMINATE_CONFIRMATION_REQUIRED")
        record = self._read(run_id)
        pid, pgid = record.get("pid"), record.get("process_group_id")
        if not pid or not pgid:
            raise ValueError("OWNED_PROCESS_GROUP_NOT_FOUND")
        if pgid != os.getpgid(pid) if os.name != "nt" else False:
            raise ValueError("PROCESS_OWNERSHIP_CHECK_FAILED")
        try:
            os.killpg(int(pgid), signal.SIGTERM)
            time.sleep(0.25)
            try:
                os.killpg(int(pgid), 0)
                os.killpg(int(pgid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass
        record.update({"status": RunStatus.TERMINATED.value, "stage": "TERMINATED", "finished_at": _now(), "cancel_requested": True, "termination_reason": "force_terminated_owned_process_group", "gpu_cleanup_status": "NOT VERIFIED IN CURRENT ENVIRONMENT"})
        self._write(record)
        return record

    def enforce_limit(self, run_id: str) -> dict[str, Any]:
        record = self._read(run_id)
        limit = record.get("time_limit_seconds")
        if limit is not None and record.get("status") in {RunStatus.STARTING.value, RunStatus.RUNNING.value, RunStatus.CANCEL_REQUESTED.value, RunStatus.CANCELLING.value}:
            started = record.get("started_at")
            if started and time.time() - datetime.fromisoformat(started).timestamp() > float(limit):
                self.request_cancel(run_id)
                record = self._read(run_id)
                record.update({"time_limit_pending": True, "time_limit_message": "graceful cancel requested; force termination is available after grace period"})
                self._write(record)
        return record
