import os
from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]

    profile = os.getenv("BAF_PROFILE", "dev_laptop")

    if profile == "dev_laptop":
        cfg_path = root / "baf_config.dev_laptop.yaml"
    elif profile == "small_enterprise":
        cfg_path = root / "baf_config.small_enterprise.yaml"
    else:
        # fallback to the original combined config
        cfg_path = root / "baf_config.yaml"

    cfg = BAFConfig.from_file(str(cfg_path))
    print(f"Profile: {profile}")
    print("Loaded BAFConfig from:", cfg_path)
    print("Top-level keys:", list(cfg.raw.keys()))

    session = BAFSession(cfg)

    for path in [
        "/app/data/Study_Materials/notes.txt",
        "/app/data/Personal_Docs/tax.pdf",
        "~/.ssh/id_rsa",
        "./.env",
        "/tmp/other.txt",
    ]:
        r = session.classify_path(path, profile=profile)
        print(profile, "->", path, ":", r.category, r.risk_score, r.meta)
