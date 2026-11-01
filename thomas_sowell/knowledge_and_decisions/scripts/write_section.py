"""Append source-matched agent translations of non-chapter sections."""
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("section")
    ap.add_argument("input",nargs="?")
    ap.add_argument("--finish",action="store_true")
    args=ap.parse_args()
    progress=json.loads((ROOT/"翻译进度.json").read_text(encoding="utf-8"))
    sec=next(s for s in progress["other_sections"] if s["id"]==args.section)
    assert sec["status"]!="translated"
    pages=json.loads((ROOT/"data/pages.json").read_text(encoding="utf-8"))[sec["pdf_start"]-1:sec["pdf_end"]]
    expected=[(p["pdf_page"],b) for p in pages for b in p["blocks"]]
    sec.setdefault("chinese_file",f"chapters/{sec['title']}（中文）.md")
    path=ROOT/sec["chinese_file"]
    t=path.read_text(encoding="utf-8") if path.exists() else f"# {sec['title']}\n\n"
    ids=re.findall(r"source-id:\s*(p\d+-\d+)",t)
    assert ids==[b["id"] for _,b in expected[:len(ids)]]
    if args.input:
        chunk=json.loads(Path(args.input).read_text(encoding="utf-8"))
        segment=expected[len(ids):len(ids)+len(chunk)]
        assert [b["id"] for _,b in segment]==[v["id"] for v in chunk]
        lastpage=expected[len(ids)-1][0] if ids else sec["pdf_start"]-1
        for v,(page,b) in zip(chunk,segment):
            for pg in range(lastpage+1,page+1):
                t+=f'\n<a id="pdf-{pg:03d}"></a><!-- PDF physical page {pg} -->\n'
            lastpage=page
            t+=f'\n<!-- source-id: {b["id"]} -->\n'+v["text"]+"\n"
        ids.extend(v["id"] for v in chunk)
    sec["status"]="in_progress"
    if args.finish:
        assert len(ids)==len(expected)
        lastpage=expected[-1][0] if expected else sec["pdf_start"]-1
        for pg in range(lastpage+1,sec["pdf_end"]+1):
            t+=f'\n<a id="pdf-{pg:03d}"></a><!-- PDF physical page {pg} -->\n'
        sec["status"]="translated"
    path.write_text(t.rstrip()+"\n",encoding="utf-8",newline="\n")
    sec.update(source_blocks_checked=len(ids),last_completed_source_id=ids[-1] if ids else None,
               chinese_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               chinese_characters=len(re.findall(r"[\u4e00-\u9fff]",t)))
    progress["next_step"]=f"继续{sec['title']}，下一来源{expected[len(ids)][1]['id']}" if len(ids)<len(expected) else f"{sec['title']}分块已保存；检查原注与语言后继续其他资料。"
    (ROOT/"翻译进度.json").write_text(json.dumps(progress,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(dict(section=sec["id"],saved=len(ids),total=len(expected),status=sec["status"]),ensure_ascii=False))
if __name__=="__main__": main()
