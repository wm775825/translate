"""Read the canonical Chinese draft by source physical pages for language review."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("start",type=int);ap.add_argument("end",type=int,nargs="?")
    args=ap.parse_args();end=args.end or args.start
    assert 1<=args.start<=end<=568 and end-args.start<=7
    p=json.loads((ROOT/"翻译进度.json").read_text(encoding="utf-8"))
    for item in sorted(p["chapters"]+p["other_sections"],key=lambda s:s["pdf_start"]):
        if item["pdf_start"]>end or item["pdf_end"]<args.start or "chinese_file" not in item:continue
        t=(ROOT/item["chinese_file"]).read_text(encoding="utf-8")
        definitions=dict(re.findall(r"^\[\^([^\]]+)\]: (.*)$",t,re.M))
        t=re.split(r"\n## (?:本章|序言)原注",t)[0]
        markers=list(re.finditer(r'<a id="pdf-(\d+)"></a>',t))
        for i,m in enumerate(markers):
            pg=int(m[1])
            if not args.start<=pg<=end:continue
            text=t[m.end():markers[i+1].start() if i+1<len(markers) else len(t)]
            text=re.sub(r"<!-- source-id:\s*(p\d+-\d+).*?-->",r"[\1]",text,flags=re.S)
            text=re.sub(r"<!--.*?-->","",text,flags=re.S).strip()
            print(f"\n=== 原PDF {pg} ===\n{text}")
            for n in dict.fromkeys(re.findall(r"\[\^([^\]]+)\]",text)):
                if re.search(r"[\u4e00-\u9fff]",definitions.get(n,"")):
                    print(f"\n[原注 {n}] {definitions[n]}")
if __name__=="__main__":main()
