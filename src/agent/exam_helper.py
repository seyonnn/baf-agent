import os
import uuid

from ..baf.baf_wrapper import baf_list_dir, baf_read_file  # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STUDY_DIR = os.path.join(BASE_DIR, "data", "Study_Materials")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")


def list_study_files(session_id: str):
    """List study files via BAF wrapper."""
    return baf_list_dir(STUDY_DIR, session_id=session_id)


def read_file_head_via_baf(path, session_id: str, max_lines=8):
    """Use BAF to read file and then take first N lines."""
    full_text = baf_read_file(path, session_id=session_id)
    lines = full_text.splitlines()
    return "\n".join(lines[:max_lines])


def build_notes_for_query(query: str, output_name: str = "study_notes_with_baf.txt"):
    session_id = str(uuid.uuid4())
    print(f"[ExamHelper] Session: {session_id}")
    print(f"[ExamHelper] Query: {query}")

    files = list_study_files(session_id=session_id)
    print(f"[ExamHelper] Found {len(files)} study files in {STUDY_DIR}")

    summary_lines = [f"### Quick notes for: {query}", ""]
    for path in files:
        summary_lines.append(f"=== {os.path.basename(path)} ===")
        summary_lines.append(read_file_head_via_baf(path, session_id=session_id))
        summary_lines.append("")

    summary_text = "\n".join(summary_lines)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, output_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"[ExamHelper] Notes written to {out_path}")


if __name__ == "__main__":
    build_notes_for_query("Unit 1 notes (BAF v0)")