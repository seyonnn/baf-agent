import os
from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    cfg_dir = root / "examples" / "exam_helper_v1" / "config"

    profile = os.getenv("BAF_PROFILE", "dev_laptop")

    if profile == "dev_laptop":
        cfg_path = cfg_dir / "baf_config.dev_laptop.exam_helper.yaml"
    elif profile == "small_enterprise":
        cfg_path = cfg_dir / "baf_config.small_enterprise.exam_helper.yaml"
    else:
        cfg_path = cfg_dir / "baf_config.exam_helper.yaml"

    cfg = BAFConfig.from_file(str(cfg_path))
    print(f"Profile: {profile}")
    print("Loaded BAFConfig from:", cfg_path)
    print("Top-level keys:", list(cfg.raw.keys()))

    session = BAFSession(cfg, agent_id="exam_helper")

    root = Path(__file__).resolve().parents[3]
    data_dir = root / "examples" / "exam_helper_v1" / "data"

    test_paths = [
        data_dir / "study_materials" / "unit1_1.txt",
        data_dir / "personal_docs" / "aadhaar_mock_1.txt",
    ]

    for path in test_paths:
        try:
            content = session.read_file(str(path), profile=profile)
            print("READ OK:", profile, path, "len", len(content))
        except PermissionError as e:
            print("BLOCKED:", e)


