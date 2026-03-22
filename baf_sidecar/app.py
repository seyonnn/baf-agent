from typing import Optional, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

from baf_core.config import BAFConfig
from baf_core.session import BAFSession

app = FastAPI()

# Load one config for now (same as exam_helper)
CONFIG_PATH = Path("examples/exam_helper_v1/config/baf_config.dev_laptop.exam_helper.yaml")
cfg = BAFConfig.from_file(CONFIG_PATH)

# Keep per-session BAFSession instances in memory
sessions: Dict[str, BAFSession] = {}


class BAFBaseRequest(BaseModel):
    session_id: str
    agent_id: str
    profile: Optional[str] = "dev_laptop"
    context: Optional[dict] = None


class ListDirRequest(BAFBaseRequest):
    path: str


class ReadFileRequest(BAFBaseRequest):
    path: str


class HttpPostRequest(BAFBaseRequest):
    url: str
    data: str


def get_session(session_id: str, agent_id: str) -> BAFSession:
    if session_id not in sessions:
        sessions[session_id] = BAFSession(cfg, agent_id=agent_id, session_id=session_id)
    return sessions[session_id]


@app.post("/baf/list_dir")
def baf_list_dir(body: ListDirRequest):
    session = get_session(body.session_id, body.agent_id)
    try:
        items: List[str] = session.list_dir(body.path, profile=body.profile)
        return {"status": "ok", "data": items, "risk": session.state.risk_score, "level": session.state.level}
    except PermissionError as e:
        return {"status": "blocked", "reason": str(e), "risk": session.state.risk_score, "level": session.state.level}


@app.post("/baf/read_file")
def baf_read_file(body: ReadFileRequest):
    session = get_session(body.session_id, body.agent_id)
    try:
        content = session.read_file(body.path, profile=body.profile)
        return {"status": "ok", "data": content, "risk": session.state.risk_score, "level": session.state.level}
    except PermissionError as e:
        return {"status": "blocked", "reason": str(e), "risk": session.state.risk_score, "level": session.state.level}


@app.post("/baf/http_post")
def baf_http_post(body: HttpPostRequest):
    session = get_session(body.session_id, body.agent_id)
    try:
        resp = session.http_post(body.url, body.data, profile=body.profile)
        return {
            "status": "ok",
            "data": {"status_code": resp.status_code, "text": resp.text},
            "risk": session.state.risk_score,
            "level": session.state.level,
        }
    except PermissionError as e:
        return {"status": "blocked", "reason": str(e), "risk": session.state.risk_score, "level": session.state.level}
