from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession


def main():
    # Load the same config file exam_helper uses
    config_path = Path("examples/exam_helper_v1/config/baf_config.dev_laptop.exam_helper.yaml")
    cfg = BAFConfig.from_file(config_path)

    session = BAFSession(cfg, agent_id="manual_test")
    profile = "dev_laptop"

    print("List study dir (should be allowed, low risk)")
    session.list_dir(
        "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/Study_Materials",
        profile=profile,
    )

    print("Read one personal file (raw, should increase risk and maybe change level)")
    try:
        raw_result = session.safe_read_file(
            "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt",
            profile=profile,
            mode="raw",
        )
        print("RAW MODE:", raw_result)
    except Exception as e:
        print("BAF blocked safe_read_file (raw):", e)

    print("Read same personal file (metadata mode)")
    try:
        meta_result = session.safe_read_file(
            "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt",
            profile=profile,
            mode="metadata",
        )
        print("METADATA MODE:", meta_result)
    except Exception as e:
        print("BAF blocked safe_read_file (metadata):", e)

    print("Try external HTTP (should be blocked or high risk)")
    try:
        session.http_post("http://127.0.0.1:5000/exfil", "test-data", profile=profile)
    except Exception as e:
        print("Blocked http_post:", e)


if __name__ == "__main__":
    main()
