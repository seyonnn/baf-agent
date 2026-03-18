import csv
import os
from datetime import datetime
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
ACTIONS_LOG_PATH = os.path.join(LOGS_DIR, "actions.log")

# Constants for categories
STUDY_DIR = os.path.join(BASE_DIR, "data", "Study_Materials")
PERSONAL_DIR = os.path.join(BASE_DIR, "data", "Personal_Docs")
KNOWN_INTERNAL_DOMAINS = {"127.0.0.1:5000", "localhost:5000"}


def _ensure_log_header():
    """Create log file with header row if empty / missing."""
    if not os.path.exists(ACTIONS_LOG_PATH) or os.path.getsize(ACTIONS_LOG_PATH) == 0:
        with open(ACTIONS_LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "session_id",
                "agent_id",
                "action_type",
                "resource",
                "bytes",
                "path_category",
                "domain_category",
            ])


def _categorize_path(path: str) -> str:
    """Return 'study', 'personal', or 'other' based on path prefix."""
    norm = os.path.abspath(path)
    study_root = os.path.abspath(STUDY_DIR)
    personal_root = os.path.abspath(PERSONAL_DIR)

    if norm.startswith(study_root):
        return "study"
    if norm.startswith(personal_root):
        return "personal"
    return "other"


def _categorize_domain(url: str) -> str:
    """Return domain category for URLs."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc
        if not host:
            return "none"
        if host in KNOWN_INTERNAL_DOMAINS:
            return "internal_known"
        return "external_unknown"
    except Exception:
        return "none"


def _log_action(session_id: str,
                agent_id: str,
                action_type: str,
                resource: str,
                nbytes: int,
                path_category: str,
                domain_category: str):
    _ensure_log_header()
    ts = datetime.utcnow().isoformat()

    with open(ACTIONS_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            ts,
            session_id,
            agent_id,
            action_type,
            resource,
            nbytes,
            path_category,
            domain_category,
        ])


# ================
# Public BAF APIs
# ================

def baf_read_file(path: str,
                  session_id: str,
                  agent_id: str = "exam_helper_v1",
                  encoding: str = "utf-8") -> str:
    """Read a file via BAF (monitor-only)."""
    path_category = _categorize_path(path)
    domain_category = "none"

    with open(path, "r", encoding=encoding) as f:
        data = f.read()

    nbytes = len(data.encode(encoding, errors="ignore"))
    _log_action(
        session_id=session_id,
        agent_id=agent_id,
        action_type="read_file",
        resource=os.path.abspath(path),
        nbytes=nbytes,
        path_category=path_category,
        domain_category=domain_category,
    )

    return data


def baf_list_dir(path: str,
                 session_id: str,
                 agent_id: str = "exam_helper_v1"):
    """List directory contents via BAF (monitor-only)."""
    path_category = _categorize_path(path)
    domain_category = "none"

    entries = []
    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if os.path.isfile(fpath):
            entries.append(fpath)

    # Approx bytes = total path string length (not that important here)
    nbytes = sum(len(e) for e in entries)
    _log_action(
        session_id=session_id,
        agent_id=agent_id,
        action_type="list_dir",
        resource=os.path.abspath(path),
        nbytes=nbytes,
        path_category=path_category,
        domain_category=domain_category,
    )
    return entries


def baf_http_post(url: str,
                  data: str,
                  session_id: str,
                  agent_id: str = "exam_helper_v1"):
    """HTTP POST via BAF (monitor-only)."""
    import requests

    domain_category = _categorize_domain(url)
    path_category = "other"
    nbytes = len(data.encode("utf-8", errors="ignore"))

    _log_action(
        session_id=session_id,
        agent_id=agent_id,
        action_type="http_post",
        resource=url,
        nbytes=nbytes,
        path_category=path_category,
        domain_category=domain_category,
    )

    resp = requests.post(url, data=data)
    return resp