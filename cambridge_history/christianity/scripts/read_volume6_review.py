from pathlib import Path
import sys,re,json
root=Path(__file__).resolve().parents[1];r=root/'第六卷';d=json.loads((r/'翻译进度.json').read_text(encoding='utf8'));p=json.loads((root/'data/volume6/pages.json').read_text(encoding='utf8'));notes=json.loads((root/'data/volume6/notes.json').read_text(encoding='utf8'))
a,b=map(int,sys.argv[1:3]);chinese='--zh' in sys.argv
for n in range(a,b+1):
 q=p[n-1];print(f'\n=== PDF {n}; ORIGINAL {q["original_page"]} ===\n{q["text"]}')
 for k in q['notes_started']:print(f'[^{k}]: {notes[k]}')
 if chinese:
  c=next(c for c in d['chapters'] if c['pdf_start']<=n<=c['pdf_end']);z=(r/c['chinese_file']).read_text(encoding='utf8');s=z.split(f'<a id="pdf-{n:03}"></a>')[1].split('<a id="pdf-')[0];s=re.sub(r'^\[\^[^\]]+\]:.*','',s,flags=re.M);print('=== CHINESE ===\n'+s)
