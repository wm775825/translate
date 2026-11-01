"""Append agent-translated, source-identified blocks without replacing old text."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chapter", type=int)
    parser.add_argument("input", nargs="?")
    parser.add_argument("--finish", action="store_true")
    parser.add_argument("--notes", help="JSON map of note number to translated text")
    args = parser.parse_args()
    progress = json.loads((ROOT / "翻译进度.json").read_text(encoding="utf-8"))
    chapter = progress["chapters"][args.chapter - 1]
    assert chapter["chapter"] == args.chapter and chapter["status"] != "translated"
    pages = json.loads((ROOT / "data/pages.json").read_text(encoding="utf-8"))
    expected = [(p["pdf_page"], b) for p in pages[chapter["pdf_start"] - 1:chapter["pdf_end"]]
                for b in p["blocks"]]
    path = ROOT / chapter["chinese_file"]
    existing = path.read_text(encoding="utf-8") if path.exists() else (
        f"# 第{args.chapter}章 {chapter['title']}\n\n"
        f"> 中文阶段译稿。正文对应原PDF物理第{chapter['pdf_start']}—{chapter['pdf_end']}页。\n")
    ids = re.findall(r"source-id:\s*(p\d+-\d+)", existing)
    assert ids == [b["id"] for _, b in expected[:len(ids)]], "已有译稿不是连续前缀，拒绝覆盖。"
    if args.input:
        entries = json.loads(Path(args.input).read_text(encoding="utf-8"))
        segment = expected[len(ids):len(ids) + len(entries)]
        assert [v["id"] for v in entries] == [b["id"] for _, b in segment]
        additions = []
        current_page = expected[len(ids) - 1][0] if ids else None
        for item, (page, block) in zip(entries, segment):
            if page != current_page:
                additions.append(f'\n<a id="pdf-{page:03d}"></a><!-- PDF physical page {page} -->\n')
                current_page = page
            text = item["text"]
            if not text:
                assert block["kind"] == "heading" and page <= chapter["pdf_start"] + 1
                additions.append(f'<!-- source-id: {block["id"]}; represented in chapter title -->\n')
            else:
                additions.append(f'\n<!-- source-id: {block["id"]} -->\n')
                additions.append(("## " if block["kind"] == "heading" else "") + text + "\n")
        existing += "".join(additions)
        ids += [v["id"] for v in entries]
    if args.finish:
        assert len(ids) == len(expected), "正文未译齐。"
        original = json.loads((ROOT / "data/notes.json").read_text(encoding="utf-8"))[f"chapter{args.chapter}"]
        custom = json.loads(Path(args.notes).read_text(encoding="utf-8")) if args.notes else {}
        wanted = {f"c{args.chapter:02d}-{n['number']}" for n in original}
        calls = set(re.findall(r"\[\^([^\]]+)\](?!:)", existing))
        assert calls == wanted, f"引注未对应：missing={wanted-calls} extra={calls-wanted}"
        existing += "\n## 本章原注\n\n"
        for note in original:
            body = custom.get(str(note["number"]), note["text"])
            existing += f"[^c{args.chapter:02d}-{note['number']}]: {body}\n\n"
        chapter["status"] = "translated"
        chapter["translated_note_count"] = len(original)
    else:
        chapter["status"] = "in_progress"
    path.write_text(existing.rstrip() + "\n", encoding="utf-8", newline="\n")
    chapter["last_completed_source_id"] = ids[-1] if ids else None
    chapter["source_blocks_checked"] = len(ids)
    chapter["chinese_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    chapter["chinese_characters"] = len(re.findall(r"[\u4e00-\u9fff]", existing))
    progress["completed_chapters"] = sum(c["status"] == "translated" for c in progress["chapters"])
    progress["last_completed_pdf_page"] = expected[len(ids) - 1][0] if ids else None
    progress["next_step"] = (f"继续第{args.chapter}章，从{expected[len(ids)][1]['id']}开始。"
                             if len(ids) < len(expected) else f"第{args.chapter}章正文已保存；核对原注和语言后接续下一章。")
    save(ROOT / "翻译进度.json", progress)
    print(json.dumps({"chapter": args.chapter, "saved_blocks": len(ids), "total_blocks": len(expected),
                      "status": chapter["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
