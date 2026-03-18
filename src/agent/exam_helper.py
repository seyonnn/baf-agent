import os

# Resolve base dir (repo root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
STUDY_DIR = os.path.join(BASE_DIR, "data", "study_materials")
OUTPUT_DIR = os.path.join(BASE_DIR, "data")


def list_study_files():
    """Return full paths of all files in Study_Materials."""
    if not os.path.isdir(STUDY_DIR):
        raise FileNotFoundError(f"Study directory not found: {STUDY_DIR}")

    files = []
    for fname in os.listdir(STUDY_DIR):
        fpath = os.path.join(STUDY_DIR, fname)
        if os.path.isfile(fpath):
            files.append(fpath)
    return sorted(files)


def read_file_head(path, max_lines=5):
    """Read first max_lines from a text file for crude summary."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def build_crude_summary():
    files = list_study_files()
    print(f"[ExamHelper] Found {len(files)} study files in {STUDY_DIR}")

    summary_lines = []
    for path in files:
        summary_lines.append(f"=== {os.path.basename(path)} ===")
        summary_lines.append(read_file_head(path))
        summary_lines.append("")  # blank line between files

    summary_text = "\n".join(summary_lines)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "study_notes_day1.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"[ExamHelper] Summary written to {out_path}")


if __name__ == "__main__":
    build_crude_summary()