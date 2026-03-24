# Architecture: How BAF-Agent fits around your agents

This document explains **where BAF-Agent sits**, how requests flow through it, and why it focuses on both **access control** and **output shaping**.

You can use this as a mental model when integrating BAF into new agents or when explaining the design to your team.

---

## 1. Big picture

At a high level, BAF-Agent sits between your agent and its environment:

> **Agent ↔ BAF-Agent ↔ Files / HTTP**

- The **agent** can be anything: a LangChain app, an MCP tools server, a custom Python bot.  
- **BAF-Agent** is a lightweight firewall layer implemented by `BAFSession`.  
- **Resources** are things the agent can touch: local files, network endpoints, etc.

Instead of letting the agent call `open()` or `requests.post()` directly, you funnel those calls through BAF, which applies a **central policy** and logs everything.

---

## 2. Core components

BAF-Agent v2 is organized around a few key pieces:

- **Policy config (YAML)**  
  - Defines path groups (`secrets`, `personal`, `study`, …).  
  - Defines domain categories (`internal_trusted`, everything else).  
  - Defines risk rules and thresholds (how actions affect the risk score and level).  
  - Defines tool modes per profile (e.g. metadata‑only for secrets in `small_enterprise`).

- **BAFSession (runtime firewall)**  
  - Loaded from `BAFConfig` + YAML.  
  - Tracks per‑session state: risk score, autonomy level (L2/L1/L0), logs.  
  - Exposes methods:
    - `safe_read_file(path, profile, mode=...)`
    - `read_file(path, profile)`
    - `list_dir(path, profile)`
    - `http_post(url, data, profile)`

- **Integrations (frontends)**  
  - LangChain tools that call BAFSession instead of raw I/O.  
  - MCP tools that call BAFSession for file/HTTP operations.  
  - Future sidecar/HTTP endpoints that proxy non‑Python agents.

---

## 3. Request flow (step-by-step)

This is what happens when an agent calls a BAF‑protected tool like “read this file”:

1. **Agent makes a tool call**  
   - LangChain agent calls `read_local_doc(path=...)`.  
   - MCP client invokes `tools/call` with `{ "name": "read_file", "arguments": { "path": "..." } }`.

2. **Tool forwards to BAFSession**  
   - The tool calls `BAF_SESSION.safe_read_file(path, profile, mode=...)`.

3. **BAF normalizes and classifies the resource**  
   - Paths are **canonicalized** (expand `~`, resolve `..`, normalize symlinks as much as possible).  
   - The canonical path is matched against configured path groups (`secrets`, `personal`, etc.).  
   - Domains are classified as `internal_known` or `external_unknown` based on `internal_trusted` in the YAML.

4. **BAF updates risk and level**  
   - Each action has a **risk rule** (e.g. `read_secrets`, `external_http`, `large_http_post`).  
   - BAF adds the appropriate delta to the session’s risk score.  
   - Thresholds map risk score → **L2 / L1 / L0**:
     - L2: low risk, most benign actions allowed.  
     - L1: elevated risk, external HTTP or sensitive paths may be blocked.  
     - L0: high risk, strict blocking of sensitive resources.

5. **BAF enforces a decision**  
   - Based on:
     - Profile policy (e.g. explicit `block` on `http_post` for some profiles).  
     - Current level (L2/L1/L0).  
     - Resource classification (e.g. `secrets` path on L1/L0).  
   - BAF either:
     - Allows the action.  
     - Allows with output shaping (metadata/summary instead of raw).  
     - Blocks the action with a `PermissionError`.

6. **BAF logs the event**  
   - Each call produces a CSV log entry with:
     - Timestamp, session id, agent id, session label.  
     - Action (`safe_read_file`, `http_post`, …).  
     - Resource (canonical path or URL).  
     - Profile, matched path group, base rule.  
     - Domain category (for HTTP).  
     - Risk delta, resulting risk score and level.  
     - Decision (allow/block).

7. **Tool returns a safe result to the agent**  
   - For allowed file reads, tools return either:
     - Raw content (when policy permits), or  
     - Summaries/metadata, clearly annotated.  
   - For blocked actions, tools return a friendly message like `[BAF blocked HTTP POST] …`, so the agent and user understand what happened.

---

## 4. Two key roles: access control + output shaping

BAF-Agent intentionally focuses on **two orthogonal controls**.

### 4.1. Resource access control

This is about **what** the agent can touch.

- Paths:  
  - Policies can treat:
    - `data/Study_Materials` as low‑risk.  
    - `data/Personal_Docs` or `secrets` as high‑risk.  
  - Access outside allowed roots can be scored as L0 and blocked entirely.

- HTTP:  
  - Policies classify domains as `internal_known` vs `external_unknown`.  
  - External HTTP calls at higher risk levels (L1/L0) can be blocked.  
  - Large payloads (e.g. megabyte‑scale exfil attempts) can be blocked by size.

This control ensures that even if the agent is fully compromised at the prompt level, it does not have **system‑level reach** into arbitrary files or exfil channels.

### 4.2. Output shaping control

This is about **what shape** of data the agent receives.

Even when access is allowed, you may not want the agent to see full raw contents of certain resources. For example:

- You might allow the agent to know **that a secret exists**, but not its exact value.  
- You might allow a short snippet or summary, but not the entire document.

BAF-Agent implements this via `safe_read_file` modes:

- `raw`: full contents.  
- `summary`: truncated or summarized text.  
- `metadata`: file name, size, timestamps, and a small preview.  
- `redacted`: content with sensitive patterns stripped (email addresses, long numbers, etc.).

Policies decide which mode applies per profile and path group. Tools are then written to **respect and surface** this mode to the agent.

The net effect: even if a prompt‑injected chain tries to read secrets, the agent only receives **safe, policy‑approved views** of those resources.

---

## 5. Library vs sidecar deployment

BAF-Agent v2 is primarily a **library** you import into Python agents:

- Direct method calls (`safe_read_file`, `http_post`).  
- Best for LangChain, MCP tools, and other Python‑first stacks.

The longer‑term v3 vision is:

> **Sidecar firewall** that runs as a separate process and exposes HTTP APIs.

In that model:

- The agent (in any language) calls a local HTTP endpoint like `/safe_read_file` or `/http_post`.  
- The sidecar runs BAFSession internally with the same YAML policies.  
- You get the same access control and output shaping with a **language‑agnostic** interface.

The sidecar pattern keeps your application logic clean and language‑agnostic, while centralizing security concerns in a dedicated firewall process.

---

## 6. Putting it all together

When you integrate BAF-Agent as designed:

- Every file/HTTP tool call flows through a **single, auditable firewall layer**.  
- Policies live in YAML, so you can:
  - Tighten rules for production.  
  - Experiment safely on a dev laptop.  
- Logs give you a **forensic trace** of what agents attempted to do, successful or not.  
- Access control and output shaping work together to constrain even prompt‑injected or misbehaving agents.

Keep this architecture in mind as you read the other docs and examples:

- `docs/quickstart_python_agent.md` – minimal Python integration.  
- `docs/langchain_guide.md` – LangChain tools + BAF.  
- `docs/mcp_tools_guide.md` – MCP tools + BAF.  
- `docs/quickstart_sidecar_http.md` – sidecar / HTTP deployment path (forward‑looking).

All of them are just different **front doors** into the same core: a behavioural firewall that stands between your agents and the world.