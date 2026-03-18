import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STUDY_DIR = os.path.join(BASE_DIR, "data", "Study_Materials")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")


def list_study_files():
    if not os.path.isdir(STUDY_DIR):
        raise FileNotFoundError(f"Study directory not found: {STUDY_DIR}")

    files = []
    for fname in os.listdir(STUDY_DIR):
        fpath = os.path.join(STUDY_DIR, fname)
        if os.path.isfile(fpath):
            files.append(fpath)
    return sorted(files)


def read_file_head(path, max_lines=8):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def build_notes_for_query(query: str, output_name: str = "study_notes.txt"):
    """
    Very simple behavior:
    - Ignores query for now (we just log it).
    - Reads all study files and builds a combined notes file.
    """
    files = list_study_files()
    print(f"[ExamHelper] Query: {query}")
    print(f"[ExamHelper] Found {len(files)} study files in {STUDY_DIR}")

    summary_lines = [f"### Quick notes for: {query}", ""]
    for path in files:
        summary_lines.append(f"=== {os.path.basename(path)} ===")
        summary_lines.append(read_file_head(path))
        summary_lines.append("")  # blank line

    summary_text = "\n".join(summary_lines)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, output_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"[ExamHelper] Notes written to {out_path}")


if __name__ == "__main__":
    # For now, hardcode a sample query
    build_notes_for_query("Unit 1 quick notes", output_name="study_notes_day2.txt")