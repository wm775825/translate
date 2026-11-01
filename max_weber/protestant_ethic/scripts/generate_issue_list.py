from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/history/新教伦理与资本主义精神_中文二校稿_v1.md"
OUT = ROOT / "tmp/reports/二校问题清单.md"


ISSUE_RULES = [
    ("长句", lambda s: len(s) >= 120, "拆句；先主干，后补限定。"),
    ("超长句", lambda s: len(s) >= 180, "必须重写；不要保留原德语句法。"),
    ("括号解释过重", lambda s: ("（" in s or "(" in s) and len(s) >= 80, "考虑把括号拆成独立句，或改为前后两句。"),
    ("逗号/分号堆叠", lambda s: s.count("，") + s.count("；") >= 5, "减少并列层级，明确因果、转折或补充关系。"),
    (
        "抽象名词堆叠",
        lambda s: sum(s.count(w) for w in ["差异", "差别", "现象", "性质", "关系", "意义", "结构", "形式", "发展", "程度", "基础", "作用"]) >= 4,
        "把抽象名词改成具体动作或判断。",
    ),
    (
        "翻译腔",
        lambda s: any(x in s for x in ["具有", "呈现", "以此为", "以其", "所造成", "所要求", "相联系", "相适应", "加以", "从属于", "取向", "在这个意义上"]),
        "改成现代中文表达，避免德式名词化。",
    ),
    (
        "逻辑连接密集",
        lambda s: sum(s.count(w) for w in ["因此", "从而", "于是", "不过", "然而", "因为", "所以", "既", "又", "不仅", "而且", "相反"]) >= 3,
        "重排论证关系；必要时分成“前提-结论”。",
    ),
]


def mostly_foreign(sentence: str) -> bool:
    ignored = set(">，。；：、“”‘’（）()《》—-·0123456789.%:/;,.'\"")
    chars = [char for char in sentence if not char.isspace() and char not in ignored]
    if not chars:
        return False
    cjk = sum(1 for char in chars if "\u4e00" <= char <= "\u9fff")
    latin = sum(1 for char in chars if ("A" <= char <= "Z") or ("a" <= char <= "z"))
    return latin > 40 and cjk / max(1, len(chars)) < 0.15


def priority(score: int, length: int, page: int) -> str:
    if page in (1, 94, 95, 96) and score < 4:
        return "P3"
    if score >= 5 or length >= 220:
        return "P1"
    if score >= 3:
        return "P2"
    return "P3"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    page_matches = list(re.finditer(r"^## Seite\s+(\d+)\s*$", text, re.M))
    pages = []
    for index, match in enumerate(page_matches):
        page = int(match.group(1))
        start = match.start()
        end = page_matches[index + 1].start() if index + 1 < len(page_matches) else len(text)
        pages.append((page, text[start:end]))

    sentence_pattern = re.compile(r"[^。！？!?\n]+[。！？!?]?")
    issues = []
    for page, block in pages:
        for sentence in sentence_pattern.findall(block):
            sentence = sentence.strip()
            if not sentence or sentence.startswith("## Seite") or mostly_foreign(sentence):
                continue

            tags = []
            suggestions = []
            score = 0
            for name, check, suggestion in ISSUE_RULES:
                if check(sentence):
                    tags.append(name)
                    suggestions.append(suggestion)
                    score += 2 if name in ("超长句", "长句") else 1

            if score < 3:
                continue
            if page == 1 and sentence.count(".") > 20:
                continue

            unique_suggestions = []
            for suggestion in suggestions:
                if suggestion not in unique_suggestions:
                    unique_suggestions.append(suggestion)

            issues.append(
                {
                    "page": page,
                    "priority": priority(score, len(sentence), page),
                    "score": score,
                    "tags": tags,
                    "text": sentence,
                    "suggestions": unique_suggestions,
                }
            )

    order = {"P1": 0, "P2": 1, "P3": 2}
    issues.sort(key=lambda item: (order[item["priority"]], item["page"], -item["score"], -len(item["text"])))

    summary = {"P1": 0, "P2": 0, "P3": 0}
    pages_with_issues = {}
    for issue in issues:
        summary[issue["priority"]] += 1
        pages_with_issues[issue["page"]] = pages_with_issues.get(issue["page"], 0) + 1

    lines = [
        "# 《新教伦理与资本主义精神》二校问题清单",
        "",
        "基于 `新教伦理与资本主义精神_中文二校稿_v1.md` 的只读筛查生成。P1 已经过第一轮人工处理；主要由外文构成的引文不计入中文润色问题。",
        "",
        "## 总览",
        "",
        f"- 检测页数：{len(pages)}",
        f"- 问题候选：{len(issues)}",
        f"- P1 高优先级：{summary['P1']}",
        f"- P2 中优先级：{summary['P2']}",
        f"- P3 低优先级：{summary['P3']}",
        "",
        "## 优先页",
        "",
    ]

    for page, count in sorted(pages_with_issues.items(), key=lambda item: (-item[1], item[0]))[:20]:
        lines.append(f"- Seite {page}: {count} 处")

    lines += [
        "",
        "## 标签说明",
        "",
        "- 长句/超长句：中文读者需要反向拆句，优先拆成两到三句。",
        "- 括号解释过重：括号里承担了论证主干，容易断裂。",
        "- 逗号/分号堆叠：并列关系过多，逻辑层级不清。",
        "- 抽象名词堆叠：概念词太密，读者难以判断谁作用于谁。",
        "- 翻译腔：德语名词化或被动结构残留。",
        "- 逻辑连接密集：因果、转折、补充关系混在一句里。",
        "",
        "## 问题项",
        "",
    ]

    for index, issue in enumerate(issues, 1):
        snippet = issue["text"]
        if len(snippet) > 320:
            snippet = snippet[:320].rstrip() + "……"
        lines += [
            f"### {index}. {issue['priority']} / Seite {issue['page']}",
            "",
            f"- 类型：{', '.join(issue['tags'])}",
            f"- 长度：{len(issue['text'])} 字",
            "- 原句片段：",
            "",
            f"> {snippet}",
            "",
            "- 处理建议：",
        ]
        for suggestion in issue["suggestions"][:3]:
            lines.append(f"  - {suggestion}")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(OUT)
    print(f"issues={len(issues)} P1={summary['P1']} P2={summary['P2']} P3={summary['P3']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
