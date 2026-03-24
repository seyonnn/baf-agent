import os
from baf_core.session import BAFSession, BAFConfig

CONFIG_PATH = "baf_config.dev_laptop.yaml"

SECRET_PATH = "examples/exam_helper_v1/data/secrets/secret_api_key.txt"
SAFE_PATH = "examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt"

def main():
    os.environ["BAF_CONFIG_PATH"] = CONFIG_PATH
    os.environ["BAF_PROFILE"] = "small_enterprise"
    os.environ["BAF_SESSION_LABEL"] = "mcp_test_small_enterprise"

    cfg = BAFConfig.from_file(CONFIG_PATH)
    baf = BAFSession(
        config=cfg,
        agent_id="mcp_baf_tools_manual_test",
        session_label=os.getenv("BAF_SESSION_LABEL"),
    )

    print("=== PROFILE:", os.getenv("BAF_PROFILE"), "===")

    print("\n=== safe_read_file on SECRET (small_enterprise) ===")
    try:
        content = baf.safe_read_file(
            path=SECRET_PATH,
            profile="small_enterprise",
            mode=None,  # let YAML choose mode (metadata)
        )
        print("SECRET CONTENT:")
        print(repr(content))
    except Exception as e:
        print("ERROR SECRET:", repr(e))

    print("\n=== safe_read_file on SAFE (small_enterprise) ===")
    try:
        content = baf.safe_read_file(
            path=SAFE_PATH,
            profile="small_enterprise",
            mode=None,
        )
        print("SAFE CONTENT:")
        print(repr(content))
    except Exception as e:
        print("ERROR SAFE:", repr(e))

    print("\n=== http_post (small_enterprise) ===")
    try:
        resp = baf.http_post(
            url="http://127.0.0.1:5000/exfil",
            data="mcp test payload",
            profile="small_enterprise",
        )
        print("HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("HTTP ERROR:", repr(e))

if __name__ == "__main__":
    main()
