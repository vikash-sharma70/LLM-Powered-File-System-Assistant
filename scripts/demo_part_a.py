"""Manual, visual demo of all 4 Part A tools against the sample resumes/.

Run this after `python scripts/generate_sample_data.py` to see each tool's
real output printed to the console. No LLM/API key involved -- this only
exercises fs_tools.py directly.

Usage:
    python scripts/demo_part_a.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fs_tools import list_files, read_file, search_in_file, write_file  # noqa: E402

RESUMES_DIR = ROOT / "resumes"
OUTPUT_DIR = ROOT / "output"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def main() -> None:
    section("1. list_files(resumes/)  -- all files")
    all_files = list_files(str(RESUMES_DIR))
    for f in all_files:
        print(f"  {f['name']:35s} {f['size_readable']:>8s}  modified={f['modified']}")

    section("1b. list_files(resumes/, extension='.pdf')  -- filtered")
    pdf_files = list_files(str(RESUMES_DIR), extension=".pdf")
    for f in pdf_files:
        print(f"  {f['name']}")

    section("2. read_file() -- one file per format")
    for filename in ("resume_aditi_sharma.txt", "resume_sneha_iyer.docx", "resume_arjun_rao.pdf"):
        result = read_file(str(RESUMES_DIR / filename))
        print(f"\n--- {filename} ---")
        print(f"success: {result['success']}")
        print(f"metadata: {json.dumps(result['metadata'], indent=2)}")
        print(f"content preview: {result['content'][:120]!r}...")

    section("2b. read_file() -- graceful error handling")
    bad_result = read_file(str(RESUMES_DIR / "does_not_exist.pdf"))
    print(json.dumps(bad_result, indent=2))

    section("3. search_in_file() -- find 'Python' across all resumes")
    for f in all_files:
        result = search_in_file(f["path"], "Python")
        if result["match_count"] > 0:
            print(f"\n{f['name']} -> {result['match_count']} match(es)")
            for m in result["matches"]:
                print(f"  line {m['line_number']}: ...{m['context']}...")

    section("4. write_file() -- create a summary file")
    summary_path = OUTPUT_DIR / "resume_aditi_sharma_summary.txt"
    summary_text = (
        "Candidate: Aditi Sharma\n"
        "Top skill match: Python (Django, REST APIs, PostgreSQL)\n"
        "Experience: 4 years, Backend Developer at Nimbus Tech\n"
    )
    write_result = write_file(str(summary_path), summary_text)
    print(json.dumps(write_result, indent=2))
    print(f"\nVerify on disk:\n{summary_path.read_text()}")

    print("\nAll Part A tools executed successfully.")


if __name__ == "__main__":
    main()
