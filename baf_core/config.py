from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class BAFConfig:
    raw: Dict[str, Any]

    @classmethod
    def from_file(cls, path: str) -> "BAFConfig":
        config_path = Path(path).expanduser().resolve()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        text = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)  # safe_load is the recommended default.[web:182][web:187]

        if not isinstance(data, dict):
            raise ValueError("BAF config root must be a mapping (YAML dict).")

        # Minimal required keys for now – we can refine later.
        required_keys = ["paths", "domains", "risk_rules", "thresholds"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"BAF config missing required keys: {missing}")

        return cls(raw=data)
