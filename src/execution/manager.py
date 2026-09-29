from __future__ import annotations

import json
import multiprocessing
import os
import signal
import threading
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

    def __init__(self, repo_root: Path, runs_dir: Path, *, cancel_grace_seconds: float = 2.0, terminate_grace_seconds: float = 2.0) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, tuple[multiprocessing.Process, Any]] = {}
        self.cancel_grace_seconds = float(cancel_grace_seconds)
        self.terminate_grace_seconds = float(terminate_grace_seconds)

    def _path(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.json"

    def _read(self, run_id: str) -> dict[str, Any]:
        return json.loads(self._path(run_id).read_text(encoding="utf-8"))

    def _write(self, record: dict[str, Any]) -> None:
        path = self._path(record["run_id"])
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)

    def start(self, run_id: str) -> dict[str, Any]:
        record = self._read(run_id)
        record.update({"status": RunStatus.STARTING.value, "stage": "STARTING", "worker_id": f"worker-{run_id}", "heartbeat_at": _now(), "cancel_requested": False, "gpu_cleanup_status": "NOT VERIFIED IN CURRENT ENVIRONMENT"})
        self._write(record)
        ctx = multiprocessing.get_context("fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn")
        event = ctx.Event()
        process = ctx.Process(target=_algorithm_worker, args=(str(self.repo_root), run_id, event), name=f"glo-run-{run_id}")
        process.start()
        # The child calls setsid() in its entrypoint.  Wait briefly for that
        # ownership boundary before persisting the process-group identity;
        # recording the API server's inherited group would make force
        # termination correctly fail its ownership check.
        pgid = None
        parent_pgid = os.getpgrp()
        for _ in range(100):
            try:
                candidate = os.getpgid(process.pid)
            except OSError:
                break
            if candidate != parent_pgid:
                pgid = candidate
                break
            time.sleep(0.005)
        record.update({"status": RunStatus.RUNNING.value, "stage": "RUNNING", "pid": process.pid, "process_group_id": pgid, "started_at": record.get("started_at") or _now(), "heartbeat_at": _now()})
        self._write(record)
        self._handles[run_id] = (process, event)
        threading.Thread(target=self._watch, args=(run_id,), daemon=True, name=f"execution-watch-{run_id}").start()
        return record

    def _set_record(self, run_id: str, **changes: Any) -> dict[str, Any]:
        record = self._read(run_id)
        record.update(changes)
        self._write(record)
        return record

    def _owned_group_alive(self, record: dict[str, Any]) -> bool:
        pid, pgid = record.get("pid"), record.get("process_group_id")
        if not pid or not pgid:
            return False
        try:
            return os.getpgid(int(pid)) == int(pgid)
        except (OSError, ProcessLookupError):
            return False

    def _terminate_owned(self, run_id: str, final_status: RunStatus, reason: str) -> dict[str, Any]:
        record = self._read(run_id)
        pid, pgid = record.get("pid"), record.get("process_group_id")
        if not pid or not pgid or not self._owned_group_alive(record):
            record.update({"status": final_status.value, "stage": final_status.name, "finished_at": _now(), "cleanup_warning": "owned process group was already absent or ownership could not be confirmed"})
            self._write(record)
            return record
        try:
            os.killpg(int(pgid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + self.terminate_grace_seconds
        while time.monotonic() < deadline and self._owned_group_alive(record):
            time.sleep(0.05)
            record = self._read(run_id)
        if self._owned_group_alive(record):
            try:
                os.killpg(int(pgid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        record = self._read(run_id)
        record.update({"status": final_status.value, "stage": final_status.name, "finished_at": _now(), "cancel_requested": True, "termination_reason": reason, "gpu_cleanup_status": "NOT VERIFIED IN CURRENT ENVIRONMENT"})
        if self._owned_group_alive(record):
            record["cleanup_warning"] = "owned process group still appears live; cleanup is not reported as PASS"
        else:
            record["cleanup_verified"] = True
        self._write(record)
        return record

    def _watch(self, run_id: str) -> None:
        while True:
            try:
                record = self._read(run_id)
            except (OSError, ValueError):
                return
            if record.get("status") == RunStatus.CANCELLED.value and record.get("time_limit_pending"):
                record.update({"status": RunStatus.TIME_LIMIT_EXCEEDED.value, "stage": "TIME_LIMIT_EXCEEDED", "finished_at": _now(), "termination_reason": "explicit_time_limit_graceful_cancel"})
                self._write(record)
                return
            if record.get("status") in {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value, RunStatus.TERMINATED.value, RunStatus.TIME_LIMIT_EXCEEDED.value, RunStatus.STALE.value}:
                return
            limit = record.get("time_limit_seconds")
            started = record.get("started_at")
            if limit is not None and started and time.time() - datetime.fromisoformat(started).timestamp() >= float(limit):
                self._set_record(run_id, status=RunStatus.CANCEL_REQUESTED.value, stage="CANCEL_REQUESTED", cancel_requested=True, time_limit_pending=True, time_limit_reached_at=_now())
                handle = self._handles.get(run_id)
                if handle:
                    handle[1].set()
                self._set_record(run_id, status=RunStatus.CANCELLING.value, stage="CANCELLING")
                process = handle[0] if handle else None
                if process:
                    process.join(timeout=self.cancel_grace_seconds)
                record = self._read(run_id)
                if process and process.is_alive():
                    self._terminate_owned(run_id, RunStatus.TIME_LIMIT_EXCEEDED, "explicit_time_limit")
                else:
                    record = self._read(run_id)
                    record.update({"status": RunStatus.TIME_LIMIT_EXCEEDED.value, "stage": "TIME_LIMIT_EXCEEDED", "finished_at": _now(), "time_limit_pending": True})
                    self._write(record)
                return
            handle = self._handles.get(run_id)
            if handle and not handle[0].is_alive():
                # A worker that obeyed a time-limit cancel is still a time-limit outcome.
                record = self._read(run_id)
                if record.get("time_limit_pending") and record.get("status") == RunStatus.CANCELLED.value:
                    record.update({"status": RunStatus.TIME_LIMIT_EXCEEDED.value, "stage": "TIME_LIMIT_EXCEEDED", "finished_at": _now()})
                    self._write(record)
                return
            time.sleep(0.05)

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
        if os.name != "nt" and not self._owned_group_alive(record):
            raise ValueError("PROCESS_OWNERSHIP_CHECK_FAILED")
        return self._terminate_owned(run_id, RunStatus.TERMINATED, "force_terminated_owned_process_group")

    def enforce_limit(self, run_id: str) -> dict[str, Any]:
        record = self._read(run_id)
        limit = record.get("time_limit_seconds")
        if limit is not None and record.get("status") in {RunStatus.STARTING.value, RunStatus.RUNNING.value, RunStatus.CANCEL_REQUESTED.value, RunStatus.CANCELLING.value}:
            started = record.get("started_at")
            if started and time.time() - datetime.fromisoformat(started).timestamp() > float(limit):
                self.request_cancel(run_id)
                record = self._read(run_id)
                record.update({"time_limit_pending": True, "time_limit_message": "automatic graceful cancel and escalation are managed by the execution watcher"})
                self._write(record)
        return record
