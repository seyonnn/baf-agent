# baf_console/app.py

import csv
import os
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

LOG_DIR = "logs"  # adjust if your logs live elsewhere

app = FastAPI(title="BAF Console V6")

def iter_session_files() -> List[str]:
    if not os.path.isdir(LOG_DIR):
        return []
    return sorted(
        [
            os.path.join(LOG_DIR, f)
            for f in os.listdir(LOG_DIR)
            if f.startswith("baf_session_") and f.endswith(".csv")
        ]
    )

def load_session_rows(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

@app.get("/", response_class=HTMLResponse)
def index():
    # Simple HTML wrapper that hits /sessions via JS
    return """
    <html>
      <head><title>BAF Sessions</title></head>
      <body>
        <h1>BAF Sessions</h1>
        <div id="sessions"></div>
        <script>
          fetch('/sessions').then(r => r.json()).then(data => {
            const div = document.getElementById('sessions');
            if (!data.length) {
              div.innerText = 'No sessions found';
              return;
            }
            let html = '<table border="1" cellspacing="0" cellpadding="4"><tr><th>Session ID</th><th>Agent</th><th>Max Level</th><th>Files Read</th><th>Bytes Raw</th><th>Bytes Safe</th></tr>';
            for (const s of data) {
              html += `<tr>
                <td><a href="/sessions/${encodeURIComponent(s.session_id)}">${s.session_id}</a></td>
                <td>${s.agent_id}</td>
                <td>${s.max_level}</td>
                <td>${s.files_read}</td>
                <td>${s.bytes_exposed_raw}</td>
                <td>${s.bytes_exposed_safe}</td>
              </tr>`;
            }
            html += '</table>';
            div.innerHTML = html;
          });
        </script>
      </body>
    </html>
    """

@app.get("/sessions")
def list_sessions():
    """Sessions list: id, agent, max_level, files_read, raw vs safe bytes."""
    files = iter_session_files()
    sessions = []
    for path in files:
        rows = load_session_rows(path)
        if not rows:
            continue

        session_id = os.path.basename(path).replace("baf_session_", "").replace(".csv", "")
        agent_id = rows[0].get("agent_id", "")

        max_level = 0
        files_read = 0
        bytes_raw = 0
        bytes_safe = 0  # placeholder for future metadata-only bytes

        for r in rows:
            # Level
            try:
                level = int(r.get("level", "0").lstrip("L") or 0)
            except ValueError:
                level = 0
            if level > max_level:
                max_level = level

            action = r.get("action", "")
            output_mode = r.get("output_mode", "")
            resource = r.get("resource", "")

            if action == "safe_read_file":
                files_read += 1
                if output_mode == "raw":
                    # Approximate bytes exposed as length of the file content
                    try:
                        with open(resource, "rb") as f:
                            content = f.read()
                        bytes_raw += len(content)
                    except Exception:
                        # If file missing or unreadable now, just skip
                        pass
                else:
                    # In future, you could add a metadata-length approximation here
                    bytes_safe += 0

        sessions.append(
            dict(
                session_id=session_id,
                agent_id=agent_id,
                max_level=f"L{max_level}",
                files_read=files_read,
                bytes_exposed_raw=bytes_raw,
                bytes_exposed_safe=bytes_safe,
            )
        )
    return sessions

@app.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(session_id: str):
    """HTML view of all actions in a session, including output_mode."""
    # Find matching file
    path = None
    for f in iter_session_files():
        if session_id in os.path.basename(f):
            path = f
            break
    if not path:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = load_session_rows(path)
    if not rows:
        return HTMLResponse("<h1>No rows in session</h1>")

    # Build a small HTML table; assumes CSV has columns like timestamp, action, resource, output_mode, risk_score, level, decision.
    headers = list(rows[0].keys())
    html = "<html><head><title>BAF Session Detail</title></head><body>"
    html += f"<h1>Session {session_id}</h1>"
    html += '<table border="1" cellspacing="0" cellpadding="4"><tr>'
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr>"
    for r in rows:
        html += "<tr>"
        for h in headers:
            html += f"<td>{r.get(h, '')}</td>"
        html += "</tr>"
    html += "</table></body></html>"
    return HTMLResponse(html)
