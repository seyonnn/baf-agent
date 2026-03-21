from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    cfg_path = root / "baf_config.yaml"

    cfg = BAFConfig.from_file(str(cfg_path))
    print("Loaded BAFConfig from:", cfg_path)
    print("Top-level keys:", list(cfg.raw.keys()))

    session = BAFSession(cfg)

    for profile in ["dev_laptop", "small_enterprise"]:
        for path in [
            "/app/data/Study_Materials/notes.txt",
            "/app/data/Personal_Docs/tax.pdf",
            "~/.ssh/id_rsa",
            "./.env",
            "/tmp/other.txt",
        ]:
            r = session.classify_path(path, profile=profile)
            print(profile, "->", path, ":", r.category, r.risk_score, r.meta)
