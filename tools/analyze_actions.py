import csv
import os
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logs", "actions.log")

def analyze_actions():
    if not os.path.exists(LOG_PATH):
        print(f"No actions.log found at {LOG_PATH}")
        return

    sessions = set()
    actions_per_session = defaultdict(int)
    read_files_per_session = defaultdict(int)
    path_categories = defaultdict(int)
    domain_categories = defaultdict(int)
    bytes_per_action = []

    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["session_id"]
            sessions.add(sid)
            actions_per_session[sid] += 1
            if row["action_type"] == "read_file":
                read_files_per_session[sid] += 1
            path_categories[row["path_category"]] += 1
            domain_categories[row["domain_category"]] += 1
            try:
                b = int(row["bytes"])
                bytes_per_action.append(b)
            except ValueError:
                pass

    print(f"Total sessions: {len(sessions)}")
    print("Actions per session:", dict(actions_per_session))
    print("Read_file per session:", dict(read_files_per_session))
    print("Path categories:", dict(path_categories))
    print("Domain categories:", dict(domain_categories))
    if bytes_per_action:
        avg = sum(bytes_per_action) / len(bytes_per_action)
        print(f"Bytes per action: min={min(bytes_per_action)}, max={max(bytes_per_action)}, avg={avg:.2f}")

if __name__ == "__main__":
    analyze_actions()