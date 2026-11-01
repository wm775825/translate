from pathlib import Path
import sys,json
r=Path(__file__).resolve().parents[1]
p=json.loads((r/'data/volume9/pages.json').read_text(encoding='utf8'))
n=json.loads((r/'data/volume9/notes.json').read_text(encoding='utf8'))
a,b=map(int,sys.argv[1:3])
for x in p[a-1:b]:
    print(f'\n=== PDF {x["pdf_page"]}; ORIGINAL {x["original_page"]} ===\n{x["text"]}\n')
    for k in x['notes_started']:print(f'[^{k}]: {n[k]}\n')
