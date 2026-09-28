"""
API 配置（环境变量）/ API settings from environment variables.

GLOSVP_DATA_DIR                实验仓库目录，默认 <repo>/data/experiments
GLOSVP_OPTIMIZATIONS_DIR       优化运行仓库目录，默认 <repo>/data/optimizations
GLOSVP_SYSTEM_EXPERIMENTS_DIR  系统级实验仓库目录，默认 <repo>/data/system_experiments
GLOSVP_CONFIGS_DIR             场景配置目录，默认 <repo>/configs（系统级场景位于其 system/ 子目录）
GLOSVP_EXPERIMENT_TIMEOUT      单次实验同步等待上限（秒），默认 600
TESTING                        "true" 时注册 FakeBackend / FakeSystemBackend（仅软件测试）
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEV_CORS_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (3000, 5173)
]


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    optimizations_dir: Path
    system_experiments_dir: Path
    configs_dir: Path
    experiment_timeout_seconds: float
    testing: bool
    cors_origins: tuple[str, ...]

    @property
    def system_configs_dir(self) -> Path:
        return self.configs_dir / "system"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.environ.get("GLOSVP_DATA_DIR", REPO_ROOT / "data" / "experiments")),
            optimizations_dir=Path(
                os.environ.get("GLOSVP_OPTIMIZATIONS_DIR", REPO_ROOT / "data" / "optimizations")
            ),
            system_experiments_dir=Path(
                os.environ.get("GLOSVP_SYSTEM_EXPERIMENTS_DIR", REPO_ROOT / "data" / "system_experiments")
            ),
            configs_dir=Path(os.environ.get("GLOSVP_CONFIGS_DIR", REPO_ROOT / "configs")),
            experiment_timeout_seconds=float(os.environ.get("GLOSVP_EXPERIMENT_TIMEOUT", "600")),
            testing=_env_flag("TESTING"),
            cors_origins=tuple(DEV_CORS_ORIGINS),
        )
