from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "translated_chunks"
OUT = ROOT / "新教伦理与资本主义精神_中文译稿.md"

EXPECTED = [
    ("chunk_01_seite_001_024.md", 1, 24),
    ("chunk_02_seite_025_048.md", 25, 48),
    ("chunk_03_seite_049_072.md", 49, 72),
    ("chunk_04_seite_073_096.md", 73, 96),
]


def page_numbers(text: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(r"^## Seite\s+(\d+)\s*$", text, re.M)]


def main() -> int:
    parts = [
        "# 新教伦理与资本主义精神",
        "",
        "> 根据 `新教伦理与资本主义精神_德文原文.md` 的德文文本生成的中文初译稿。",
        "> 本稿保留原 PDF 页码标题，供后续校订和对照。",
        "",
    ]

    all_pages: list[int] = []
    missing_files: list[str] = []
    bad_ranges: list[str] = []

    for filename, start, end in EXPECTED:
        path = CHUNK_DIR / filename
        if not path.exists():
            missing_files.append(str(path))
            continue

        text = path.read_text(encoding="utf-8").strip()
        pages = page_numbers(text)
        expected_pages = list(range(start, end + 1))
        if pages != expected_pages:
            bad_ranges.append(f"{filename}: expected {start}-{end}, found {pages[:3]}...{pages[-3:] if pages else []}")

        all_pages.extend(pages)
        parts.append(text)
        parts.append("")

    expected_all = list(range(1, 97))
    if missing_files or all_pages != expected_all or bad_ranges:
        print("Merge validation failed.", file=sys.stderr)
        if missing_files:
            print("Missing files:", file=sys.stderr)
            for item in missing_files:
                print(f"  {item}", file=sys.stderr)
        if bad_ranges:
            print("Unexpected chunk page ranges:", file=sys.stderr)
            for item in bad_ranges:
                print(f"  {item}", file=sys.stderr)
        if all_pages != expected_all:
            missing_pages = sorted(set(expected_all) - set(all_pages))
            duplicate_pages = sorted({page for page in all_pages if all_pages.count(page) > 1})
            print(f"Missing pages: {missing_pages}", file=sys.stderr)
            print(f"Duplicate pages: {duplicate_pages}", file=sys.stderr)
        return 1

    OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(OUT)
    print(f"pages={len(all_pages)}")
    print(f"chars={len(OUT.read_text(encoding='utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
