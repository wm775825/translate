"""Validate saved source correspondence and completed chapter structure."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    progress = load("翻译进度.json")
    structure = load("data/structure.json")
    pages = load("data/pages.json")
    notes = load("data/notes.json")
    errors = []
    if hashlib.sha256((ROOT / progress["source_pdf"]).read_bytes()).hexdigest() != progress["source_sha256"]:
        errors.append("原始PDF哈希不符。")
    if [p["pdf_page"] for p in pages] != list(range(1, progress["pdf_pages"] + 1)):
        errors.append("逐页数据不完整或顺序异常。")
    full = (ROOT / "知识与决策（英文全文）.md").read_text(encoding="utf-8")
    full_anchors = list(map(int, re.findall(r'<a id="pdf-(\d+)"></a>', full)))
    if full_anchors != list(range(1, progress["pdf_pages"] + 1)):
        errors.append("英文全文页锚缺失、重复或顺序异常。")
    inventory = []
    for item in structure["chapters"] + structure["other_sections"]:
        expected = list(range(item["pdf_start"], item["pdf_end"] + 1))
        inventory += expected
        path = ROOT / item["english_file"]
        if not path.is_file():
            errors.append("缺少英文稿：" + item["english_file"])
            continue
        text = path.read_text(encoding="utf-8")
        anchors = list(map(int, re.findall(r'<a id="pdf-(\d+)"></a>', text)))
        if anchors != expected:
            errors.append("英文稿页锚不符：" + item["english_file"])
    if sorted(inventory) != list(range(1, progress["pdf_pages"] + 1)):
        errors.append("章节及卷首卷末未完整覆盖PDF，或范围重复。")
    image_count = 0
    seen = set()
    for page in pages:
        for image in page["images"]:
            if image["asset"] in seen:
                continue
            seen.add(image["asset"])
            path = ROOT / image["asset"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != image["sha256"]:
                errors.append("图像缺失或改变：" + image["asset"])
            image_count += 1
    completed = []
    for chapter in progress["chapters"]:
        if chapter["status"] != "translated":
            continue
        path = ROOT / chapter["chinese_file"]
        if not path.exists():
            errors.append("缺少已完成中文稿：" + chapter["chinese_file"])
            continue
        text = path.read_text(encoding="utf-8")
        source = pages[chapter["pdf_start"] - 1:chapter["pdf_end"]]
        expected = [b["id"] for p in source for b in p["blocks"]]
        actual = re.findall(r"source-id:\s*(p\d+-\d+)", text)
        if actual != expected:
            errors.append("中文稿来源标识缺失、重复或顺序异常：" + chapter["chinese_file"])
        anchors = list(map(int, re.findall(r'<a id="pdf-(\d+)"></a>', text)))
        if anchors != list(range(chapter["pdf_start"], chapter["pdf_end"] + 1)):
            errors.append("中文稿物理页锚不符：" + chapter["chinese_file"])
        calls = re.findall(r"\[\^([^\]]+)\](?!:)", text)
        definitions = re.findall(r"^\[\^([^\]]+)\]:", text, re.M)
        expected_notes = {f"c{chapter['chapter']:02d}-{v['number']}" for v in notes[f"chapter{chapter['chapter']}"]}
        if set(calls) != expected_notes or set(definitions) != expected_notes or len(definitions) != len(set(definitions)):
            errors.append("原注引用或定义不符：" + chapter["chinese_file"])
        if "\ufffd" in text or "(cid:" in text:
            errors.append("中文稿仍有提取占位字符：" + chapter["chinese_file"])
        completed.append({"chapter": chapter["chapter"], "source_blocks": len(expected),
                          "notes": len(expected_notes),
                          "chinese_characters": len(re.findall(r"[\u4e00-\u9fff]", text))})
    for path in [ROOT / "知识与决策（英文全文）.md", *list((ROOT / "chapters").glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        for image in re.findall(r"!\[[^\]]*\]\(<([^>]+)>\)", text):
            if not (path.parent / image).resolve().is_file():
                errors.append("图像链接失效：" + str(path.relative_to(ROOT)))
    result = {"all_checks_passed": not errors, "source_pdf_unchanged": True if not errors else None,
              "source_pages": len(pages), "chapters_inventoried": len(structure["chapters"]),
              "images_verified": image_count, "completed_chapters": completed,
              "scope": "结构及文件身份检查，不代替语义复核或PDF排版校核。", "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
