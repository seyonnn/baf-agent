# Guide: Using BAF-Agent with LangChain

This guide shows how to plug **BAF-Agent v2** into a LangChain agent so that:

- All file reads go through `BAFSession.safe_read_file` (with output shaping).  
- All HTTP POSTs go through `BAFSession.http_post` (with exfil guards).  

You can use this pattern to retrofit BAF onto existing LangChain tools with minimal changes.

---

## 1. Mental model: where BAF sits

In a typical LangChain setup, your agent uses tools that do side‑effects:

- Tools that read local files (notes, docs, configs).  
- Tools that call HTTP APIs (internal services, external SaaS).

With BAF-Agent, the picture becomes:

> **LLM / LangChain Agent → Tools → BAFSession → Files / HTTP**

Your tools no longer call `open()` or `requests.post()` directly.  
Instead, they talk to a **single BAF session** that:

- Classifies paths/domains using your YAML policy.  
- Tracks risk over the session (L2 → L1 → L0).  
- Enforces blocking and output shaping per profile.

---

## 2. Prerequisites

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e .

export BAF_CONFIG_PATH="baf_config.dev_laptop.yaml"
export BAF_PROFILE="dev_laptop"
```

We’ll assume you’re comfortable with:

- Basic LangChain concepts (LLM, tools, agent executor).  
- Python 3.9 and virtualenv usage.

---

## 3. Create a BAFSession for your LangChain app

In your LangChain app (or in a small wrapper module), create one shared `BAFSession`:

```python
from baf_core.config import BAFConfig
from baf_core.session import BAFSession

def make_baf_session() -> BAFSession:
    cfg = BAFConfig.from_file("baf_config.dev_laptop.yaml")
    return BAFSession(
        config=cfg,
        agent_id="langchain_exam_helper",
        session_label="interactive",
    )

BAF_SESSION = make_baf_session()
```

You will inject `BAF_SESSION` into your tools instead of using raw file/HTTP calls.

---

## 4. Wrap file access tools with safe_read_file

### 4.1. A simple “read document” tool (before BAF)

A typical LangChain tool might look like:

```python
# BEFORE: raw file access (not recommended)
from langchain.tools import tool

@tool("read_local_doc")
def read_local_doc(path: str) -> str:
    "Read a local text file and return its contents."
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
```

This bypasses any firewall logic and lets prompt‑injected instructions read arbitrary files.

### 4.2. The same tool using BAFSession.safe_read_file

Replace it with:

```python
from langchain.tools import tool
from .baf_session import BAF_SESSION  # the shared session from above

PROFILE = "dev_laptop"  # or inject dynamically if needed

@tool("read_local_doc")
def read_local_doc(path: str) -> str:
    """
    Read a local text file via BAF.
    The firewall decides whether to return raw, summary, or metadata.
    """
    result = BAF_SESSION.safe_read_file(
        path=path,
        profile=PROFILE,
        mode=None,  # let the policy decide (raw/summary/metadata)
    )

    # Normalize for the agent: return a string that is safe to show the LLM.
    mode = result.get("mode")
    if mode == "raw":
        return result["content"]
    if mode in ("summary", "redacted"):
        return result["content"]
    if mode == "metadata":
        preview = result.get("preview", "")
        name = result.get("name", "")
        size = result.get("size", 0)
        return f"[BAF metadata only] {name} ({size} bytes). Preview: {preview!r}"
    # Fallback
    return str(result)
```

What this gives you:

- Sensitive paths (e.g. `secrets`, `personal`) can be forced to **metadata/summary** by policy.  
- The LLM never sees the full secret if your policy says it should not.  
- BAF logs and scores every read for later analysis or red‑team review.

---

## 5. Wrap HTTP tools with http_post

### 5.1. A simple “POST data” tool (before BAF)

You might currently have:

```python
# BEFORE: raw HTTP exfil path
import requests
from langchain.tools import tool

@tool("http_post")
def http_post_tool(url: str, data: str) -> str:
    "POST data to a URL and return the status."
    resp = requests.post(url, data=data)
    return f"Status: {resp.status_code}"
```

Prompt injection can easily turn this into an exfiltration channel.

### 5.2. The same tool using BAFSession.http_post

Change it to:

```python
from langchain.tools import tool
from .baf_session import BAF_SESSION

PROFILE = "dev_laptop"

@tool("http_post")
def http_post_tool(url: str, data: str) -> str:
    """
    POST data via BAF. High-risk exfil attempts will be blocked.
    """
    try:
        resp = BAF_SESSION.http_post(
            url=url,
            data=data,
            profile=PROFILE,
        )
        return f"Status: {resp.status_code}"
    except PermissionError as e:
        # Surface a safe, human-readable explanation to the agent / user
        return f"[BAF blocked HTTP POST] {e}"
```

Now:

- Domains are classified as `internal_known` vs `external_unknown` based on your YAML.  
- External or oversized payloads can be scored and **blocked**.  
- BAF enforces **max payload size** and **network timeouts**, so the agent cannot hang or stream huge secrets out.

---

## 6. Wire tools into your LangChain agent

Assuming you have an LLM and want to use these tools:

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

from .baf_file_tools import read_local_doc
from .baf_http_tools import http_post_tool

def make_agent() -> AgentExecutor:
    llm = ChatOpenAI(model="gpt-4o-mini")  # or your preferred model

    tools = [read_local_doc, http_post_tool]

    prompt = """You are a helpful assistant. 
Use tools to read documents or call HTTP APIs, but respect any safety messages.
"""

    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )
    return AgentExecutor(agent=agent, tools=tools, verbose=True)
```

From here, your application logic doesn’t have to know about BAF:

- It just calls `agent_executor.invoke({"input": "..."})`.  
- Tools enforce firewall policies transparently.

---

## 7. Running the included example

This repo ships with a LangChain integration under:

- `examples/langchain_baf_agent/`

To run it (from repo root):

```bash
source .venv/bin/activate
export BAF_CONFIG_PATH="baf_config.dev_laptop.yaml"
export BAF_PROFILE="dev_laptop"

python -m examples.langchain_baf_agent.main
```

In the logs and console output you’ll see:

- File reads going through `safe_read_file` with debug prints (metadata/summary when required).  
- HTTP POST attempts being blocked when they target untrusted endpoints or exceed payload limits.  
- The agent still functioning normally for benign study‑style interactions.

---

## 8. Design tips for your own LangChain projects

- **Single session per conversation**  
  Create one `BAFSession` per user session or conversation, so risk scores and logs are coherent.

- **Never mix raw `open()` / `requests.post()`**  
  Once BAF is in your app, treat `safe_read_file` and `http_post` as your **only** file/HTTP primitives. This makes reasoning and auditing much easier.

- **Use profiles to separate environments**  
  For example:
  - `dev_laptop` – more permissive, for local experiments.  
  - `small_enterprise` – stricter, for demos and production‑like setups.

- **Surface blocks as normal tool outputs**  
  Returning `[BAF blocked ...]` from tools helps the agent and user understand what happened, without exposing sensitive details.

---

## 9. Where to go next

- See `docs/mcp_tools_guide.md` for using the same BAF core with MCP tools.  
- Run `python -m tools.redteam_harness` to see how your policies behave under simulated exfil attempts.  
- Explore and tune the YAML policy packs (`baf_config.dev_laptop.yaml`, `baf_config.small_enterprise.yaml`) to match your own environment.

With these patterns in place, you can gradually retrofit BAF-Agent across your LangChain toolset and gain a clear, enforceable security boundary around your agents.