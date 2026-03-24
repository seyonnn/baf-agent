# Quickstart (Preview): Running BAF-Agent as an HTTP sidecar

> Status: **preview / roadmap**  
> This document describes the intended shape of an HTTP sidecar for BAF-Agent.  
> v2 focuses on Python library usage; the sidecar pattern is the next step toward v3.

The sidecar pattern lets you run BAF-Agent as a **separate process** that any agent (Python, Node, Go, etc.) can call over HTTP:

> **Agent (any language) → HTTP → BAF sidecar → Files / HTTP**

This turns BAF-Agent into a **language‑agnostic behavioural firewall** that can sit next to any agent process.

---

## 1. Why a sidecar?

Running BAF-Agent as a sidecar has a few advantages:

- **Language independence**  
  Any agent stack that can make HTTP calls can use the same firewall.

- **Separation of concerns**  
  Your agent focuses on reasoning and tool orchestration.  
  The sidecar focuses on policies, logging, and enforcement.

- **Operational flexibility**  
  You can update policies or the firewall implementation **without** changing the agent code.

---

## 2. Conceptual API

A minimal HTTP sidecar would expose endpoints roughly like:

- `POST /safe_read_file`  
  Read a file via BAF policies, with output shaping.

- `POST /http_post`  
  Send an HTTP POST via BAF, with domain classification and exfil guards.

The request/response bodies are simple JSON.

### 2.1. /safe_read_file

**Request**

```json
POST /safe_read_file
Content-Type: application/json

{
  "path": "data/Study_Materials/unit1_notes.txt",
  "profile": "dev_laptop",
  "mode": null
}
```

- `path`: path to read (string).  
- `profile`: BAF profile name (optional; may default).  
- `mode`: desired mode (`raw`, `summary`, `metadata`, `redacted`, or null to let policy decide).

**Response (examples)**

```json
{
  "mode": "raw",
  "content": "Full file contents here..."
}
```

or:

```json
{
  "mode": "metadata",
  "name": "secret_api_key.txt",
  "size": 58,
  "mtime": 1774238077.926103,
  "preview": "MOCK_SECRET_API_KEY=sk-test-1234567890-DO-NOT-USE-IN-PROD\n"
}
```

If the action is blocked:

```json
{
  "error": "BAF_blocked",
  "message": "BAF blocked safe_read_file on data/Secrets/api_key.txt at level L0"
}
```

### 2.2. /http_post

**Request**

```json
POST /http_post
Content-Type: application/json

{
  "url": "http://127.0.0.1:5000/exfil",
  "data": "payload-goes-here",
  "profile": "dev_laptop"
}
```

**Response (allowed)**

```json
{
  "status_code": 200,
  "ok": true
}
```

**Response (blocked)**

```json
{
  "error": "BAF_blocked",
  "message": "BAF blocked http_post to http://127.0.0.1:5000/exfil at level L1 (session_label=...)"
}
```

---

## 3. Sketching a minimal sidecar implementation

> Note: The repo currently focuses on in‑process usage.  
> This section shows what a future sidecar implementation might look like using FastAPI or Flask.

### 3.1. Basic FastAPI sidecar (sketch)

```python
# sidecar/main.py (preview sketch)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from baf_core.config import BAFConfig
from baf_core.session import BAFSession

app = FastAPI(title="BAF-Agent Sidecar")

cfg = BAFConfig.from_file("baf_config.dev_laptop.yaml")
SESSION = BAFSession(config=cfg, agent_id="sidecar", session_label="sidecar_http")

DEFAULT_PROFILE = "dev_laptop"

class SafeReadFileRequest(BaseModel):
    path: str
    profile: str | None = None
    mode: str | None = None

class HttpPostRequest(BaseModel):
    url: str
    data: str
    profile: str | None = None

@app.post("/safe_read_file")
def safe_read_file_endpoint(req: SafeReadFileRequest):
    profile = req.profile or DEFAULT_PROFILE
    try:
        result = SESSION.safe_read_file(
            path=req.path,
            profile=profile,
            mode=req.mode,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail={"error": "BAF_blocked", "message": str(e)})

@app.post("/http_post")
def http_post_endpoint(req: HttpPostRequest):
    profile = req.profile or DEFAULT_PROFILE
    try:
        resp = SESSION.http_post(
            url=req.url,
            data=req.data,
            profile=profile,
        )
        return {"status_code": resp.status_code, "ok": resp.ok}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail={"error": "BAF_blocked", "message": str(e)})
```

Run:

```bash
uvicorn sidecar.main:app --reload --port 8000
```

Now any agent that can make HTTP requests can call `http://localhost:8000/safe_read_file` and `/http_post` instead of touching the filesystem or network directly.

---

## 4. Using the sidecar from a non‑Python agent (example: Node)

Here’s a small Node.js example of calling the sidecar:

```js
// node-agent/sidecarClient.js
import fetch from "node-fetch";

const SIDECAR_URL = "http://127.0.0.1:8000";

export async function safeReadFile(path) {
  const res = await fetch(`${SIDECAR_URL}/safe_read_file`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path,
      profile: "dev_laptop",
      mode: null
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`[BAF sidecar error] ${JSON.stringify(err)}`);
  }

  return await res.json();
}

export async function httpPost(url, data) {
  const res = await fetch(`${SIDECAR_URL}/http_post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      data,
      profile: "dev_laptop"
    })
  });

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(`[BAF blocked] ${JSON.stringify(body)}`);
  }
  return body;
}
```

Your Node‑based agent can now build tools around `safeReadFile` / `httpPost` in exactly the same way as the Python examples, but without linking Python directly.

---

## 5. Design considerations

When you build out the sidecar for real, keep these in mind:

- **One session per agent/user**  
  - Consider mapping each agent conversation or client connection to a separate `BAFSession`, so risk scores and logs remain coherent.

- **Stateless vs sticky sessions**  
  - You can keep sessions in memory (simpler, but not horizontally scalable), or store session state externally if you need multiple sidecar instances.

- **Authentication and trust**  
  - In production, you should authenticate callers (e.g. mTLS, API keys) so that only your agents can talk to the sidecar.

- **No secret leakage in error messages**  
  - The sidecar should return clear, human‑readable reasons for blocks, but never echo secrets or sensitive data in error bodies.

---

## 6. Where this fits in the roadmap

Today (v2), BAF-Agent is **Python‑first**, with:

- Library APIs (`BAFSession`) for LangChain + MCP.  
- YAML policies and red‑team harnesses.

The **sidecar** is the path to v3:

- **Any‑agent firewall**: any runtime that can call HTTP can be protected.  
- **Operational control**: ops teams can deploy/update BAF policies independently of agent code.  
- **Security layering**: you can combine BAF sidecars with existing API gateways, service meshes, and infra‑level firewalls.

As you adopt BAF-Agent today, favor designs that:

- Keep file/HTTP accesses **behind a small abstraction** in your agent.  
- Make it easy to swap that abstraction from in‑process calls to HTTP sidecar calls later.

That way, you’ll be ready to flip from “Python library” to “sidecar firewall” with minimal agent changes when v3 arrives.