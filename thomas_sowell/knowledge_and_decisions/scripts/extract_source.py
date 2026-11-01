"""Initial source import. Never resets an existing translation."""
import collections
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "知识与决策.pdf"
TITLES = [
    ("The Role of Knowledge", "知识的作用", 3),
    ("Decision-Making Process", "决策过程", 21),
    ("Economic Trade-Offs", "经济权衡", 45),
    ("Social Trade-Offs", "社会权衡", 81),
    ("Political Trade-Offs", "政治权衡", 114),
    ("An Overview", "总览", 150),
    ("Historical Trends", "历史趋势", 163),
    ("Trends in Economics", "经济领域的趋势", 167),
    ("Trends in Law", "法律领域的趋势", 229),
    ("Trends in Politics", "政治领域的趋势", 305),
]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def is_heading(line):
    text = line["text"]
    return (bool(re.fullmatch(r"Chapter\s+(?:\d+|i)", text, re.I))
            or line["font_size"] >= 18
            or line["bold_fraction"] > .7 and len(text) < 110)


def blocks(lines, page):
    out = []
    current = []
    prev = None
    for line in lines:
        heading = is_heading(line)
        split = (heading or prev is not None and
                 (is_heading(prev) or line["top"] - prev["bottom"] > 7))
        if split and current:
            out.append({"kind": "paragraph", "text": " ".join(current)})
            current = []
        if heading:
            out.append({"kind": "heading", "text": line["text"]})
        else:
            current.append(line["text"])
        prev = line
    if current:
        out.append({"kind": "paragraph", "text": " ".join(current)})
    for n, block in enumerate(out, 1):
        block["id"] = f"p{page:03d}-{n:02d}"
    return out


def markdown(pages, title):
    lines = ["# " + title, "", "> 英文提取稿；定位使用当前PDF物理页，非原纸本页码。", ""]
    for page in pages:
        n = page["pdf_page"]
        lines += [f'<a id="pdf-{n:03d}"></a>',
                  f"<!-- PDF physical page {n}; printed page mapping unavailable -->", ""]
        for image in page["images"]:
            lines += [f'![原书图像](<{image["asset"]}>)', ""]
        for block in page["blocks"]:
            prefix = "## " if block["kind"] == "heading" else ""
            lines += [f'<!-- source-id: {block["id"]} -->', prefix + block["text"], ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    if (ROOT / "翻译进度.json").exists():
        raise SystemExit("已有提取数据或翻译进度，拒绝初始化覆盖。")
    reader = PdfReader(SOURCE)
    if (ROOT / "data/pages.json").exists():
        import sys
        if "--finish-existing-extraction" not in sys.argv:
            raise SystemExit("已有逐页提取数据；仅可显式继续整理，不能重新初始化。")
        imported = json.loads((ROOT / "reports/导入记录.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == imported["sha256"]
        pages = json.loads((ROOT / "data/pages.json").read_text(encoding="utf-8"))
        assert len(pages) == len(reader.pages)
        image_cache = {image["sha256"]: image["asset"] for page in pages for image in page["images"]}
    else:
        pages = []
        image_cache = {}
        with pdfplumber.open(SOURCE) as document:
            for n, page in enumerate(document.pages, 1):
                raw = page.extract_text_lines(layout=False, strip=True, return_chars=True)
                lines = []
                for line in raw:
                    chars = [c for c in line["chars"] if c["text"].strip()]
                    if not chars:
                        continue
                    size = collections.Counter(round(c["size"], 2) for c in chars).most_common(1)[0][0]
                    lines.append({
                        "text": norm(line["text"]), "x0": round(line["x0"], 2),
                        "top": round(line["top"], 2), "bottom": round(line["bottom"], 2),
                        "font_size": size,
                        "bold_fraction": round(sum("Bold" in c["fontname"] for c in chars) / len(chars), 3),
                    })
                images = []
                if page.images:
                    for j, image in enumerate(reader.pages[n - 1].images, 1):
                        data = image.data
                        digest = hashlib.sha256(data).hexdigest()
                        if digest not in image_cache:
                            suffix = Path(image.name).suffix or ".bin"
                            asset = f"assets/source-p{n:03d}-{j:02d}{suffix}"
                            (ROOT / asset).write_bytes(data)
                            image_cache[digest] = asset
                        images.append({"asset": image_cache[digest], "sha256": digest})
                links = []
                for annot in page.annots or []:
                    links.append({k: annot.get(k) for k in ["x0", "top", "x1", "bottom", "uri"]})
                pages.append({"pdf_page": n, "raw_text": "\n".join(l["text"] for l in lines),
                              "lines": lines, "blocks": blocks(lines, n), "images": images,
                              "links": links})
                page.close()
                if n % 50 == 0:
                    print(f"Extracted {n}/{len(document.pages)} pages", flush=True)
    save(ROOT / "data/pages.json", pages)
    covers = []
    for page in pages:
        match = re.fullmatch(r"Chapter\s+(\d+|i|s|io)", norm(page["raw_text"]), re.I)
        if match:
            token = match[1].lower()
            num = {"i": 1, "s": 5, "io": 10}[token] if token in {"i", "s", "io"} else int(token)
            covers.append((num, page["pdf_page"]))
    assert [n for n, _ in covers] == list(range(1, 11)), covers
    find = lambda title: next(p["pdf_page"] for p in pages if norm(p["raw_text"]) == title)
    part1 = find("Part I SOCIAL INSTITUTIONS")
    part2 = find("Part II TRENDS AND ISSUES")
    note_start = next(p["pdf_page"] for p in pages if p["raw_text"].startswith("NOTES\nPreface"))
    index_start = next(p["pdf_page"] for p in pages if p["raw_text"].startswith("INDEX\n"))
    preface_start = next(p["pdf_page"] for p in pages if p["raw_text"].startswith("PREFACE TO THE"))
    ack_start = next(p["pdf_page"] for p in pages if p["raw_text"].startswith("ACKNOWLEDGMENTS"))
    chapters = []
    for i, ((num, start), (en, zh, printed)) in enumerate(zip(covers, TITLES)):
        end = covers[i + 1][1] - 1 if i < 9 else note_start - 1
        if num == 6:
            end = part2 - 1
        english = f"chapters/第{num:02d}章 {zh}（英文）.md"
        chinese = f"chapters/第{num:02d}章 {zh}（中文）.md"
        chapter = {"chapter": num, "english_title": en, "title": zh,
                   "pdf_start": start, "pdf_end": end, "printed_start_from_contents": printed,
                   "english_file": english, "chinese_file": chinese, "status": "pending"}
        text = markdown(pages[start - 1:end], f"第{num:02d}章 {en}")
        # Assets are referenced relative to the chapter file.
        text = text.replace("](<assets/", "](<../assets/")
        (ROOT / english).write_text(text, encoding="utf-8", newline="\n")
        chapters.append(chapter)
    extras = [
        ("front", "版权及原书目录", 1, preface_start - 1),
        ("preface", "1996年版序言", preface_start, ack_start - 1),
        ("acknowledgments", "致谢", ack_start, part1 - 1),
        ("part1", "第一部分 社会制度", part1, part1),
        ("part2", "第二部分 趋势与问题", part2, part2),
        ("notes", "原注", note_start, index_start - 1),
        ("index", "索引", index_start, len(pages) - 3),
        ("back-cover", "封底", len(pages) - 2, len(pages) - 2),
        ("generated-toc", "电子版导航目录", len(pages) - 1, len(pages)),
    ]
    extra_sections = []
    for key, title, start, end in extras:
        path = f"chapters/{title}（英文）.md"
        text = markdown(pages[start - 1:end], title).replace("](<assets/", "](<../assets/")
        (ROOT / path).write_text(text, encoding="utf-8", newline="\n")
        extra_sections.append({"id": key, "title": title, "pdf_start": start,
                               "pdf_end": end, "english_file": path, "status": "pending"})
    (ROOT / "知识与决策（英文全文）.md").write_text(
        markdown(pages, "Knowledge and Decisions"), encoding="utf-8", newline="\n")
    notes = {}
    section = "preface"
    current = None
    for page in pages[note_start - 1:index_start - 1]:
        for block in page["blocks"]:
            text = block["text"]
            if text in {"NOTES", "Preface"}:
                continue
            chapter = re.fullmatch(r"Chapter\s+(\d+)", text)
            if chapter:
                section = f"chapter{int(chapter[1])}"
                current = None
                continue
            start = re.match(r"^(\d+)\.\s+(.*)", text)
            if start:
                current = {"number": int(start[1]), "text": start[2], "pdf_pages": [page["pdf_page"]]}
                notes.setdefault(section, []).append(current)
            elif current is not None:
                current["text"] += " " + text
                if page["pdf_page"] not in current["pdf_pages"]:
                    current["pdf_pages"].append(page["pdf_page"])
    save(ROOT / "data/notes.json", notes)
    structure = {"pdf_pages": len(pages), "parts": [part1, part2], "chapters": chapters,
                 "other_sections": extra_sections, "notes_start": note_start, "index_start": index_start,
                 "pagination": "Reflowed Calibre PDF; no fixed offset to original printed pagination."}
    save(ROOT / "data/structure.json", structure)
    audit = {"title": "Knowledge and Decisions", "author": "Thomas Sowell",
             "copyright_year": 1980, "edition_preface_year": 1996,
             "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
             "pdf_pages": len(pages), "chapter_count": len(chapters),
             "text_empty_pages": [p["pdf_page"] for p in pages if not p["raw_text"]],
             "image_assets": list(image_cache.values()), "parts": [part1, part2],
             "chapter_ranges": chapters, "note_counts": {k: len(v) for k, v in notes.items()},
             "source_chapter_label_defects": [{"pdf_page": 26, "raw": "Chapter i", "chapter": 1}, {"pdf_page": 154, "raw": "Chapter S", "chapter": 5}, {"pdf_page": 370, "raw": "Chapter io", "chapter": 10}],
             "issues": ["Bookmarks were not used as chapter boundaries; actual chapter cover and headings were checked.",
                        "Printed page starts are recorded from the original contents, not inferred per PDF page.",
                        "The source is reflowed and contains pre-existing OCR/word-joining defects; review each translated block against the PDF."]}
    save(ROOT / "reports/原书审计.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
