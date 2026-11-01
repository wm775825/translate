"""Read a small, source-located block for translation."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start", type=int, nargs="?")
    parser.add_argument("end", type=int, nargs="?")
    parser.add_argument("--notes", help="preface or chapter1 ... chapter10")
    args = parser.parse_args()
    if args.notes:
        data = json.loads((ROOT / "data/notes.json").read_text(encoding="utf-8"))
        print(json.dumps(data[args.notes], ensure_ascii=False, indent=2))
        return
    if args.start is None:
        parser.error("需要起始物理页。")
    end = args.end or args.start
    if not 1 <= args.start <= end <= 568 or end - args.start > 5:
        parser.error("每次读取1—6页；请缩小范围，以免输出被截断。")
    pages = json.loads((ROOT / "data/pages.json").read_text(encoding="utf-8"))
    for page in pages[args.start - 1:end]:
        print(f"\n=== PDF {page['pdf_page']} ===")
        for block in page["blocks"]:
            print(f"\n[{block['id']}] {block['kind']}\n{block['text']}")


if __name__ == "__main__":
    main()
