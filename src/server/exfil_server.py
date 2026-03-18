import os
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
EXFIL_LOG_PATH = os.path.join(LOGS_DIR, "exfil.log")


@app.route("/exfil", methods=["POST"])
def exfil():
    data = request.get_data(as_text=True)
    ts = datetime.utcnow().isoformat()

    with open(EXFIL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] /exfil called\n")
        f.write(data)
        f.write("\n\n" + "-" * 60 + "\n\n")

    return jsonify({"status": "ok", "message": "data received"}), 200


@app.route("/lecture_notes", methods=["GET"])
def lecture_notes():
    # Simple simulated lecture page
    content = (
        "Lecture Notes: Basics of Network Security\n\n"
        "Network security protects data in transit between devices.\n"
        "Key ideas: CIA triad, firewalls, IDS/IPS, and secure protocols.\n"
    )
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    # Default dev server on localhost:5000
    app.run(host="127.0.0.1", port=5000, debug=True)