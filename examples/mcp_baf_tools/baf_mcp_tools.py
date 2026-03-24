# examples/mcp_baf_tools/baf_mcp_tools.py

import os
import sys
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from baf_core.config import BAFConfig
from baf_core.session import BAFSession

# Central YAML + profile (override via env for flexibility)
BAF_CONFIG_PATH = os.getenv("BAF_CONFIG_PATH", os.path.join(REPO_ROOT, "baf_config.dev_laptop.yaml"))
BAF_PROFILE = os.getenv("BAF_PROFILE", "dev_laptop")  # can be "small_enterprise" etc.
MCP_AGENT_ID = "mcp_baf_tools"

_baf_session: Optional[BAFSession] = None


def get_baf_session() -> BAFSession:
    """Get (or lazily create) a shared BAF session for this MCP server."""
    global _baf_session
    if _baf_session is None:
        print("DEBUG BAF_CONFIG_PATH:", BAF_CONFIG_PATH)
        config = BAFConfig.from_file(BAF_CONFIG_PATH)
        session_label = (
            config.default_session_label
            or os.getenv("BAF_SESSION_LABEL")
            or "attack"
        )
        _baf_session = BAFSession(
            config=config,
            agent_id=MCP_AGENT_ID,
            session_label=session_label,
        )
    return _baf_session


def read_file_via_baf(path: str, mode: str = "metadata") -> str:
    """
    Read a file via BAF with an explicit output mode.

    mode options (enforced by BAF + YAML):
      - "raw"       : full contents (more allowed on dev_laptop)
      - "metadata"  : size, mtime, basic info
      - "summary"   : future summary / redacted modes
    """
    baf = get_baf_session()
    result = baf.safe_read_file(path=path, profile=BAF_PROFILE, mode=mode)

    if isinstance(result, dict) and "content" in result:
        return str(result["content"])
    return str(result)


def fetch_url_via_baf(url: str, data: str = "") -> str:
    """
    HTTP POST via BAF; all outbound POST from MCP should go through this.

    BAF will enforce domain and payload rules from the YAML policy
    (e.g., block exfil to unknown or explicitly blocked domains).
    """
    baf = get_baf_session()
    resp = baf.http_post(url=url, data=data, profile=BAF_PROFILE)
    try:
        text = resp.text
    except Exception:
        text = str(resp)
    return f"status={resp.status_code}, body={text[:200]}"
