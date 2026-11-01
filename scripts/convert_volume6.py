from pathlib import Path
from environment import poppler_tool, require_uninitialized
import collections, copy, hashlib, json, re, statistics, subprocess, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第六卷')

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'第六卷'; T=ROOT/'data/volume6'; A=R/'assets'
for p in (R,T,A): p.mkdir(exist_ok=True)
SOURCE=ROOT/'06 改革与扩张.pdf'
PDTOPPM = poppler_tool('pdftoppm')
titles=[
'改革者马丁·路德','新教在神圣罗马帝国的兴起与巩固：至1600年','激进宗教改革','17世纪的路德宗',
'共同体宗教改革：慈运理、路德与神圣罗马帝国南部','日内瓦的加尔文宗教改革','改革宗基督教的神学与礼仪','新教扩张的第二波',
'重新界定天主教：特伦托及其后','新的男性修会','女性圣德：1500—1660年','特伦托改革后的敬拜与圣徒崇敬',
'没有和谐的和平：宗教宽容的理论与实践','推行教会与社会纪律','迫害与殉道','欧洲近代早期地中海地区的宗教裁判所','宗教会谈与宽容','西方基督教与东正教',
'宗教改革与视觉艺术','近代早期基督教的仪式','音乐与宗教变迁','恶魔学：1500—1660年','科学与宗教','新的教士群体','妇女与宗教变迁',
'基督教与犹太教','安第斯基督教诸形态的本土化','伊斯兰教与东正教之间：东南欧的新教徒与天主教徒','由中国人塑造的基督教','对印度教与佛教的接受'
]
reader=PdfReader(SOURCE); bookmarks=[]
def walk(xs,depth=0):
 for x in xs:
  if isinstance(x,list): walk(x,depth+1)
  else: bookmarks.append(dict(title=x.title,pdf_start=reader.get_destination_page_number(x)+1,depth=depth))
walk(reader.outline)
dividers=[24,96,166,248,366,506]
chapters=[]
for b in bookmarks:
 m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
 if m:
  n=int(m[1]); chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
for i,c in enumerate(chapters):
 end=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 620
 c['pdf_end']=min([end]+[n-1 for n in dividers if c['pdf_start']<n<=end])
 c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md',status='pending')
other=[
 dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=15),
 dict(key='preface',title_zh='编者序',pdf_start=16,pdf_end=17),
 dict(key='chronology',title_zh='大事年表',pdf_start=18,pdf_end=23),
 *[dict(key=f'part{i+1}',title_zh='第'+['一','二','三','四','五','六'][i]+'编 '+title,pdf_start=n,pdf_end=n+1) for i,(n,title) in enumerate(zip(dividers,['路德与神圣罗马帝国','第二次宗教改革','天主教更新','化解宗派冲突','宗教、社会与文化','基督教与其他信仰']))],
 dict(key='bibliography',title_zh='参考书目',pdf_start=621,pdf_end=735),
 dict(key='index',title_zh='索引',pdf_start=736,pdf_end=774)
]
for s in other: s.update(english_file=s['title_zh']+'（英文）.md',chinese_file=s['title_zh']+'（中文）.md',status='pending')
assert sorted(n for s in chapters+other for n in range(s['pdf_start'],s['pdf_end']+1))==list(range(1,775))

def clean(s):
 for a,b in {'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'}.items(): s=s.replace(a,b)
 for mark,comb in [('´','\u0301'),('`','\u0300'),('¨','\u0308'),('˜','\u0303'),('ˇ','\u030c'),('˚','\u030a')]:
  s=re.sub(r'([A-Za-z])'+re.escape(mark),lambda m:m[1]+comb,s)
 return unicodedata.normalize('NFC',s)

def join(a,b):
 # Word breaks are retained conservatively, and reviewed against the page during translation.
 return a+' '+b if a else b

pages=[]; notes={}; warnings=[]; image_pages=[1]; last_note=None; last_sid=None; counters={}
with pdfplumber.open(SOURCE) as pdf:
 for n,pg in enumerate(pdf.pages,1):
  chapter=next((s for s in chapters if s['pdf_start']<=n<=s['pdf_end']),None)
  s=chapter or next(s for s in other if s['pdf_start']<=n<=s['pdf_end'])
  sid='ch'+str(chapter['chapter']) if chapter else s['key']; prose=bool(chapter)
  if sid!=last_sid: last_note=None;last_sid=sid
  chars=[copy.copy(c) for c in pg.chars if c['top']<585 and not (n>=26 and c['top']<60)]
  if n<26: chars=[copy.copy(c) for c in pg.chars if c['top']<585]
  folio_text=pg.crop((0,585,pg.width,min(615,pg.height))).extract_text(x_tolerance=1) or ''
  folio=re.search(r'^\s*((?:\d\s*){1,3}|[ivxlcdm]+)\s*$',folio_text,re.M)
  original=str(n-23) if n>=24 else (folio[1].replace(' ','') if folio else None)
  # Standard body = 10.46pt, quotations = 9.71pt, footnotes = 8.47pt.
  nc=[c for c in chars if abs(c['size']-8.47)<.06 and c['top']>130] if prose else []
  ntop=min((c['top'] for c in nc),default=999)
  body=[c for c in chars if not (prose and c['top']>=ntop-1 and c['size']<8.7)]
  foot=[c for c in chars if prose and c['top']>=ntop-1 and c['size']<8.7]
  # Geometric superscripts are anchored back to their body baseline before text assembly.
  supers=[c for c in body if c['text'].isdigit() and (abs(c['size']-7.32)<.08 or abs(c['size']-6.8)<.08)] if prose else []
  groups=[]
  for c in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
   if groups and abs(groups[-1][-1]['top']-c['top'])<1 and -.3<=c['x0']-groups[-1][-1]['x1']<2: groups[-1].append(c)
   else: groups.append([c])
  refs=[]
  for g in groups:
   number=''.join(c['text'] for c in g);key=f'p{n:03}-{number}';refs.append(key)
   g[0]['text']=f'[^{key}]'
   for c in g: c['top']+=3.2;c['bottom']+=3.2
   for c in g[1:]:c['text']=''
  lines=pdfplumber.utils.chars_to_textmap(body,x_tolerance=1,y_tolerance=3.5).extract_text_lines(return_chars=True) if body else []
  out=[]; buf=[];kind='body';base=min((l['x0'] for l in lines if 50<l['x0']<78),default=60)
  def flush():
   if buf:
    out.append(('> ' if kind=='quote' else '')+clean(' '.join(buf)));buf.clear()
  for l in lines:
   st=l['text'].strip()
   if not st:continue
   sizes=[c['size'] for c in l['chars'] if c['text'].strip() and c['size']>8.7]
   fs=statistics.median(sizes) if sizes else 0
   if prose and fs>10.7:
    flush();out.append(('### ' if fs<13 else '## ')+clean(st));continue
   nk='quote' if prose and 9.6<fs<9.9 else 'body'
   if nk!=kind:flush();kind=nk
   elif prose and kind=='body' and base+7<l['x0']<base+16:flush()
   elif not prose:flush()
   buf.append(st)
  flush()
  footlines=pdfplumber.utils.chars_to_textmap(foot,x_tolerance=1,y_tolerance=3).extract_text_lines(return_chars=True) if foot else []
  newdefs=[]
  for l in footlines:
   st=clean(l['text'].strip())
   # Distinguish inline second notes using whitespace geometry, not citation numbers.
   cs=sorted(l['chars'],key=lambda c:c['x0']);starts=[]
   digitgroups=[]
   for c in cs:
    if c['text'].isdigit():
     if digitgroups and abs(digitgroups[-1][-1]['top']-c['top'])<1 and -.3<=c['x0']-digitgroups[-1][-1]['x1']<1:digitgroups[-1].append(c)
     else:digitgroups.append([c])
   for g in digitgroups:
    k=''.join(c['text'] for c in g)
    before=[c for c in cs if c['x1']<=g[0]['x0']+.01 and c not in g and c['text'].strip()]
    gap=g[0]['x0']-before[-1]['x1'] if before else 99
    if (g[0] is cs[0] or gap>7) and f'p{n:03}-{k}' in refs and f'p{n:03}-{k}' not in notes:starts.append((g[0]['x0'],g[-1]['x1'],k))
   m=re.match(r'^(\d{1,3})\s+(.*)',st)
   # First-line markers sit to the left of continuation text. Right-aligned folios already removed.
   first_ok=bool(m and f'p{n:03}-{m[1]}' in refs and f'p{n:03}-{m[1]}' not in notes)
   if first_ok:
    starts=[x for x in starts if x[2]==m[1] or x[0]>l['x0']+20]
   else:starts=[x for x in starts if x[0]>l['x0']+20]
   if not starts:
    if last_note:notes[last_note]=join(notes[last_note],st)
    elif st:warnings.append(dict(page=n,unassigned_note=st))
    continue
   prefix=[c for c in cs if c['x0']<starts[0][0]-.01]
   if prefix and last_note:notes[last_note]=join(notes[last_note],clean(pdfplumber.utils.extract_text(prefix,x_tolerance=1,y_tolerance=3)))
   for i,(x0,x1,k) in enumerate(starts):
    xend=starts[i+1][0] if i+1<len(starts) else 999
    seg=[c for c in cs if c['x0']>=x1-.01 and c['x0']<xend-.01]
    val=clean(pdfplumber.utils.extract_text(seg,x_tolerance=1,y_tolerance=3).strip())
    last_note=f'p{n:03}-{k}';notes[last_note]=val;newdefs.append(last_note);counters[sid]=int(k)
  pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
  if pics and n not in image_pages:image_pages.append(n)
  text='\n\n'.join(out);refs=[k for k in refs if f'[^{k}]' in text]
  pages.append(dict(pdf_page=n,original_page=original,printed_folio=folio[1].replace(' ','') if folio else None,original_page_inferred=bool(n>=24 and not folio),section_id=sid,text=text,refs=refs,notes_started=newdefs,images=bool(pics)))
  pg.close()
  if n%100==0:print('Extracted',n,flush=True)

refs={k for p in pages for k in p['refs']}
issues=dict(unmatched_references=sorted(refs-set(notes)),unmatched_definitions=sorted(set(notes)-refs))
for s in chapters+other:
 sub=pages[s['pdf_start']-1:s['pdf_end']]
 s['source_notes']=sum(len(p['notes_started']) for p in sub)
 s['english_words_approx']=len(re.findall(r'\b[A-Za-z][A-Za-z’\'-]*\b',' '.join(p['text'] for p in sub)))
 s['conversion_issues']={k:[x for x in v if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,v in issues.items()}
d=dict(scope='第六卷；由当前代理逐章翻译，沿用前五卷术语',source_pdf=SOURCE.name,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=774,source_publication_year=2007,editor='夏伯嘉（R. Po-chia Hsia）',translation_status='in_progress',proofreading_status='pending',pdf_status='pending',chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=image_pages,extraction_warnings=warnings)
for path,val in [(R/'翻译进度.json',d),(R/'卷六结构.json',bookmarks),(ROOT/'data/volume6/pages.json',pages),(ROOT/'data/volume6/notes.json',notes)]:path.write_text(json.dumps(val,ensure_ascii=False,indent=2),encoding='utf8')
def md(p):
 n=p['pdf_page'];txt=f'<a id="pdf-{n:03}"></a>\n<!-- PDF page {n}; original page {p["original_page"] or "unnumbered"} -->\n\n'+p['text']+'\n'
 if n in image_pages:txt+=f'\n![原书PDF第{n}页图像](assets/pdf-{n:03}.png)\n'
 if p['notes_started']:txt+='\n'+'\n\n'.join(f'[^{k}]: {notes[k]}' for k in p['notes_started'])+'\n'
 return txt
toc='\n'.join(f'- [{s["title_zh"]}](#pdf-{s["pdf_start"]:03})' for s in sorted(chapters+other,key=lambda s:s['pdf_start']))
(R/'06 改革与扩张（英文全文）.md').write_text('# 剑桥基督教史 第六卷：改革与扩张，1500—1660\n\n英文转换底稿。保留全部774页锚点；正文原页码=PDF页码减23。未译部分的特殊字库、脚注、分栏及图像尚须人工复核。\n\n'+toc+'\n\n'+'\n\n---\n\n'.join(md(p) for p in pages),encoding='utf8')
for s in chapters+other:(R/s['english_file']).write_text('# '+s['title_zh']+'：英文转换底稿\n\n'+'\n\n'.join(md(p) for p in pages[s['pdf_start']-1:s['pdf_end']]),encoding='utf8')
print('Converted',len(pages),'pages,',len(notes),'notes,',len(image_pages),'image pages; issues',issues,'warnings',len(warnings),flush=True)
for n in image_pages:
 if not (A/f'pdf-{n:03}.png').exists():subprocess.run([str(PDTOPPM),'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(A/f'pdf-{n:03}')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
