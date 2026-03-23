# examples/mcp_baf_tools/baf_mcp_tools.py

import os
import sys
from typing import Optional, Dict, Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from baf_core.config import BAFConfig
from baf_core.session import BAFSession

BAF_PROFILE = "dev_laptop"
MCP_AGENT_ID = "mcp_baf_tools"

_baf_session: Optional[BAFSession] = None


def _build_minimal_raw_config() -> Dict[str, Any]:
    """
    Minimal raw config so BAFConfig(raw=...) and BAFSession work
    without needing to load any external file.
    Adjust paths/domains if you want stricter rules.
    """
    return {
        "paths": {
            # Treat a "secrets" directory as sensitive (adjust to your real path)
            "secrets": ["./secrets"],
            # Optional: personal files
            "personal": ["./personal"],
        },
        "domains": {
            "internal_trusted": ["127.0.0.1", "localhost"],
        },
        "risk_rules": {
            "secrets_read": 80,
            "personal_read": 40,
            "read_other": 0,
            "external_http": 40,
            "large_http_post": 40,
            "http_post_large_threshold": 10240,
        },
        "thresholds": {
            "L2_to_L1": 40,
            "L1_to_L0": 80,
        },
        "profiles": {
            BAF_PROFILE: {
                "use_paths": ["secrets", "personal"],
            },
        },
        "tools": {
            "file_read": {
                "default_mode": "raw",
                "profiles": {
                    BAF_PROFILE: "raw",
                },
            },
        },
    }


def get_baf_session() -> BAFSession:
    global _baf_session
    if _baf_session is None:
        raw_cfg = _build_minimal_raw_config()
        config = BAFConfig(raw=raw_cfg)
        _baf_session = BAFSession(config=config, agent_id=MCP_AGENT_ID)
    return _baf_session


def read_file_via_baf(path: str, mode: str = "raw") -> str:
    baf = get_baf_session()
    result = baf.safe_read_file(path=path, profile=BAF_PROFILE, mode=mode)

    if isinstance(result, dict) and "content" in result:
        return str(result["content"])
    return str(result)


def fetch_url_via_baf(url: str, data: str = "") -> str:
    baf = get_baf_session()
    resp = baf.http_post(url=url, data=data, profile=BAF_PROFILE)
    try:
        text = resp.text
    except Exception:
        text = str(resp)
    return f"status={resp.status_code}, body={text[:200]}"
