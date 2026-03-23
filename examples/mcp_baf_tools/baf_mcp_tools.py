# examples/mcp_baf_tools/baf_mcp_tools.py

import os
import sys
import yaml
from typing import Optional, Dict, Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from baf_core.config import BAFConfig
from baf_core.session import BAFSession

BAF_CONFIG_PATH = os.path.join(REPO_ROOT, "baf_config.dev_laptop.yaml")
BAF_PROFILE = "dev_laptop"
MCP_AGENT_ID = "mcp_baf_tools"

_baf_session: Optional[BAFSession] = None


def get_baf_session() -> BAFSession:
    global _baf_session
    if _baf_session is None:
        print("DEBUG BAF_CONFIG_PATH:", BAF_CONFIG_PATH)

        # Use the same helper as LangChain: load from YAML file directly
        config = BAFConfig.from_file(BAF_CONFIG_PATH)
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
