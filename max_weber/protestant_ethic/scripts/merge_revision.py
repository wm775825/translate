from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "data/revision_chunks"
OUT = ROOT / "tmp/collections/新教伦理与资本主义精神_中文二校稿_v1.md"

PARTITIONS = [(start, min(start + 5, 96)) for start in range(1, 97, 6)]


def chunk_name(start: int, end: int) -> str:
    return f"revision_{start:03d}_{end:03d}.md"


def page_numbers(text: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(r"^## Seite\s+(\d+)\s*$", text, re.M)]


def scan() -> tuple[list[str], list[str], list[str]]:
    done: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []

    for start, end in PARTITIONS:
        name = chunk_name(start, end)
        path = CHUNK_DIR / name
        if not path.exists():
            missing.append(name)
            continue

        text = path.read_text(encoding="utf-8")
        pages = page_numbers(text)
        expected = list(range(start, end + 1))
        if pages != expected:
            invalid.append(f"{name}: expected {expected}, found {pages}")
        else:
            done.append(name)

    return done, missing, invalid


def main() -> int:
    done, missing, invalid = scan()
    print(f"done={len(done)} missing={len(missing)} invalid={len(invalid)}")
    if missing:
        print("missing:")
        for name in missing:
            print(f"  {name}")
    if invalid:
        print("invalid:", file=sys.stderr)
        for item in invalid:
            print(f"  {item}", file=sys.stderr)
        return 1
    if missing:
        return 2

    parts = [
        "# 新教伦理与资本主义精神",
        "",
        "> 中文二校稿 v1。根据德文原文和中文初译逐页对照修订，保留原 PDF 页码标题。",
        "",
    ]

    all_pages: list[int] = []
    for start, end in PARTITIONS:
        text = (CHUNK_DIR / chunk_name(start, end)).read_text(encoding="utf-8").strip()
        all_pages.extend(page_numbers(text))
        parts.append(text)
        parts.append("")

    expected_all = list(range(1, 97))
    if all_pages != expected_all:
        print("Full page coverage failed.", file=sys.stderr)
        print(f"missing_pages={sorted(set(expected_all) - set(all_pages))}", file=sys.stderr)
        print(f"duplicate_pages={sorted({page for page in all_pages if all_pages.count(page) > 1})}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(OUT)
    print(f"pages={len(all_pages)}")
    print(f"chars={len(OUT.read_text(encoding='utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
