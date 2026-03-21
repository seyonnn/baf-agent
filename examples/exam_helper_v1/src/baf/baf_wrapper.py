import os
from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession


BASE_DIR = Path(__file__).resolve().parents[4]  # repo root


# Simple per-process session cache for exam_helper_v1
_EXAM_HELPER_SESSIONS: dict[str, BAFSession] = {}


def _get_baf_session(session_id: str) -> BAFSession:
    if session_id in _EXAM_HELPER_SESSIONS:
        return _EXAM_HELPER_SESSIONS[session_id]

    cfg_path = (
        BASE_DIR
        / "examples"
        / "exam_helper_v1"
        / "config"
        / "baf_config.dev_laptop.exam_helper.yaml"
    )

    cfg = BAFConfig.from_file(str(cfg_path))
    session = BAFSession(cfg, agent_id="exam_helper_v1", session_id=session_id)
    _EXAM_HELPER_SESSIONS[session_id] = session
    return session


# ================
# Public BAF APIs (v2)
# ================


def baf_read_file(
    path: str,
    session_id: str,
    agent_id: str = "exam_helper_v1",
    encoding: str = "utf-8",
) -> str:
    """
    Read a file via BAF core (v2).
    Signature kept for backward compatibility with v1 example.
    """
    session = _get_baf_session(session_id)
    return session.read_file(path, profile="dev_laptop")


def baf_list_dir(
    path: str,
    session_id: str,
    agent_id: str = "exam_helper_v1",
):
    """
    List directory contents via BAF core (v2).
    """
    session = _get_baf_session(session_id)
    return session.list_dir(path, profile="dev_laptop")


def baf_http_post(
    url: str,
    data: str,
    session_id: str,
    agent_id: str = "exam_helper_v1",
):
    """
    HTTP POST via BAF core (v2).
    """
    session = _get_baf_session(session_id)
    return session.http_post(url, data, profile="dev_laptop")
