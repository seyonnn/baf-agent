# Quickstart: Protect a Python agent in ~10 lines

This guide shows how to wrap a simple Python agent with **BAF-Agent v2** so that:

- File reads go through `safe_read_file`, with **metadata/summary** for sensitive paths.
- HTTP POSTs go through `http_post`, with **exfil attempts blocked** based on your policy.

You can adapt this pattern to any Python agent framework.

---

## 1. Install and configure BAF-Agent

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e .

export BAF_CONFIG_PATH="baf_config.dev_laptop.yaml"
export BAF_PROFILE="dev_laptop"
```

- `BAF_CONFIG_PATH` points to your YAML policy pack (paths, domains, risk rules).
- `BAF_PROFILE` selects the profile inside that YAML (e.g. `dev_laptop`, `small_enterprise`).

---

## 2. Minimal policy‑protected agent (single file example)

Create `examples/minimal_agent.py` with:

```python
from baf_core.config import BAFConfig
from baf_core.session import BAFSession

def main():
    # 1) Load config and create a BAF session
    cfg = BAFConfig.from_file("baf_config.dev_laptop.yaml")
    session = BAFSession(
        config=cfg,
        agent_id="minimal_agent",
        session_label="demo",
    )

    # 2) Use safe_read_file instead of open()
    result = session.safe_read_file(
        path="data/Study_Materials/unit1_notes.txt",
        profile="dev_laptop",
        mode=None,  # let policy decide: raw / summary / metadata
    )

    print("File read result:", result)

    # 3) Use http_post instead of requests.post()
    try:
        resp = session.http_post(
            url="http://127.0.0.1:5000/exfil",
            data="demo-payload",
            profile="dev_laptop",
        )
        print("HTTP status:", resp.status_code)
    except PermissionError as e:
        print("HTTP blocked by BAF:", e)

if __name__ == "__main__":
    main()
```

Run:

```bash
python -m examples.minimal_agent
```

What you’ll see depends on your policy pack, but typically:

- If the file path is benign, you’ll get **raw or summary** content.  
- If the path is sensitive (e.g. `secrets`/`personal` group), you’ll see **metadata** or **summary** instead of the full file.  
- The HTTP POST to `127.0.0.1:5000/exfil` will be **blocked** for untrusted profiles.

---

## 3. Why this is safer than raw `open()` and `requests.post()`

By funnelling all file and HTTP actions through `BAFSession`:

- Paths are **normalized and classified** before access is granted.  
- Risk score and autonomy level are updated over time (L2 → L1 → L0).  
- Sensitive reads can be forced into **metadata/summary** mode.  
- External HTTP exfil attempts can be **scored and blocked** centrally.

This creates a single, auditable choke point for your agent’s side effects.

---

## 4. Next steps

- See `docs/langchain_guide.md` for a LangChain integration using the same pattern.  
- See `docs/mcp_tools_guide.md` for MCP tools backed by BAF-Agent.  
- Run `python -m tools.redteam_harness` to exercise built‑in exfil scenarios against your policies.

Once you’re comfortable with this minimal example, you can replace your agent’s direct `open()` and `requests.post()` calls with `BAFSession.safe_read_file` and `BAFSession.http_post` to get the same protection in your own project.