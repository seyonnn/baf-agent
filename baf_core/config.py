# baf_core/config.py

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class BAFConfig:
    raw: Dict[str, Any]
    default_session_label: Optional[str] = None

    @classmethod
    def from_file(cls, path: str) -> "BAFConfig":
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        default_session_label = data.get("default_session_label")

        cfg = cls(
            raw=data,
            default_session_label=default_session_label,
        )

        validate_config(cfg)
        return cfg


def validate_config(config: BAFConfig) -> None:
    """Basic sanity checks to avoid dangerously weak configs."""
    raw = config.raw

    paths = raw.get("paths", {})
    domains = raw.get("domains", {})

    secrets_paths = paths.get("secrets")
    internal_trusted = domains.get("internal_trusted")

    if not secrets_paths:
        print(
            "[BAF WARNING] paths.secrets is not configured. "
            "Sensitive files may not be classified correctly."
        )

    if not internal_trusted:
        print(
            "[BAF WARNING] domains.internal_trusted is empty. "
            "All HTTP destinations will be treated as external/unknown."
        )
