# BAF Sidecar (Day V4)

This sidecar exposes the BAFSession APIs over HTTP so non‑Python agents
(Node, Go, MCP, etc.) can use BAF for file and HTTP access control.

## Run

```bash
uvicorn baf_sidecar.app:app --port 7070
```

## Example requests

List a directory:

```bash
curl -X POST http://127.0.0.1:7070/baf/list_dir \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sidecar-test-1",
    "agent_id": "test_agent",
    "profile": "dev_laptop",
    "path": "/tmp"
  }'
```

Read a personal file:

```bash
curl -X POST http://127.0.0.1:7070/baf/read_file \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sidecar-test-1",
    "agent_id": "test_agent",
    "profile": "dev_laptop",
    "path": "/Users/poovaragamukeshkumar/Documents/GitHub/baf-agent/examples/exam_helper_v1/data/personal_docs/college_id_mock_1.txt"
  }'
```