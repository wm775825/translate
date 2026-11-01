from pathlib import Path
from environment import poppler_tool, require_uninitialized
import collections,copy,hashlib,json,re,statistics,subprocess,unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第七卷')

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'第七卷';T=ROOT/'data/volume7';A=R/'assets'
for p in (R,T,A):p.mkdir(exist_ok=True)
assert not (R/'翻译进度.json').exists(),'Initial conversion only; do not reset an existing translation.'
SOURCE=ROOT/'07 启蒙、复兴与革命.pdf'
reader=PdfReader(SOURCE);bookmarks=[]
def walk(xs,depth=0):
 for x in xs:
  if isinstance(x,list):walk(x,depth+1)
  else:bookmarks.append(dict(title=x.title,pdf_start=reader.get_destination_page_number(x)+1,depth=depth))
walk(reader.outline)
titles=['欧洲大陆的天主教','欧洲大陆的新教','大不列颠与爱尔兰','经济与社会中的教会','欧洲的天主教教士','欧洲世界的新教教士群体','面向听众：欧洲的讲道与演说','基督教教育','基督教与性别','民众宗教','犹太教与基督教的关系','建筑与基督教','基督教与科学的兴起：1660—1815','启蒙运动对基督教的批判','基督教启蒙运动','詹森主义与耶稣会在各国遭到取缔','北大西洋世界的福音复兴','宗教宽容与基督徒再合一运动：1660—1789','伊比利亚美洲的基督教','1765年以前的英属、法属北美','非洲的基督教','南亚与东南亚的基督教','东亚的基督教','基督教与其他世界宗教的相遇','美国革命与宗教：1765—1815','基督教与反对奴隶制、奴隶贸易的运动','1794年以前的法国革命与宗教','法国革命与宗教：1795—1815','革命时代欧洲的基督教复兴运动：1790—1815']
dividers=[28,102,264,386,510]
chapters=[]
for b in bookmarks:
 m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
 if m:
  n=int(m[1]);chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
for i,c in enumerate(chapters):
 end=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 610
 c['pdf_end']=min([end]+[n-1 for n in dividers if c['pdf_start']<n<=end])
 c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md',status='pending')
other=[dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=14),dict(key='acknowledgements',title_zh='致谢',pdf_start=15,pdf_end=15),dict(key='introduction',title_zh='导论',pdf_start=16,pdf_end=27),*[dict(key=f'part{i+1}',title_zh='第'+['一','二','三','四','五'][i]+'编 '+title,pdf_start=n,pdf_end=n+1) for i,(n,title) in enumerate(zip(dividers,['欧洲世界的教会、国家与社会：1660—1780','欧洲世界的基督徒生活：1660—1780','运动与挑战','非欧洲世界的基督教发展','革命与基督教世界']))],dict(key='chronology',title_zh='大事年表',pdf_start=611,pdf_end=617),dict(key='bibliography',title_zh='参考书目',pdf_start=618,pdf_end=666),dict(key='index',title_zh='索引',pdf_start=667,pdf_end=695)]
for s in other:s.update(english_file=s['title_zh']+'（英文）.md',chinese_file=s['title_zh']+'（中文）.md',status='pending')
assert sorted(n for s in chapters+other for n in range(s['pdf_start'],s['pdf_end']+1))==list(range(1,len(reader.pages)+1))
def clean(s):
 for a,b in {'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'}.items():s=s.replace(a,b)
 for mark,comb in [('´','\u0301'),('`','\u0300'),('¨','\u0308'),('˜','\u0303'),('ˇ','\u030c'),('˚','\u030a'),('ˆ','\u0302'),('¸','\u0327')]:
  s=re.sub(r'([A-Za-z])'+re.escape(mark),lambda m:m[1]+comb,s)
 return unicodedata.normalize('NFC',s)
pages=[];notes={};warnings=[];last_sid=None;note_mode=False;last_note=None;callmap={}
image_pages=[1,17,49,244,246,248,249,252,403,428,449,453,475,484,*range(611,618)]
with pdfplumber.open(SOURCE) as pdf:
 for n,pg in enumerate(pdf.pages,1):
  chapter=next((s for s in chapters if s['pdf_start']<=n<=s['pdf_end']),None)
  s=chapter or next(s for s in other if s['pdf_start']<=n<=s['pdf_end']);sid='ch'+str(chapter['chapter']) if chapter else s['key']
  prose=bool(chapter) or sid=='introduction'
  if sid!=last_sid:last_sid=sid;note_mode=False;last_note=None;callmap={}
  if pg.height==646:bottom=585
  elif pg.height>700:bottom=670
  else:bottom=pg.height-30
  chars=[copy.copy(c) for c in pg.chars if c['top']<bottom and not (n>=16 and pg.width<pg.height and c['top']<61)]
  # The first map is vector artwork. Keep its words in the source image, outside prose.
  if n==17:chars=[c for c in chars if c['top']>=430]
  supers=[c for c in chars if c['text'].isdigit() and (abs(c['size']-7.32)<.08 or abs(c['size']-6.8)<.08)] if prose and not note_mode else []
  groups=[]
  for c in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
   if groups and abs(groups[-1][-1]['top']-c['top'])<1 and -.3<=c['x0']-groups[-1][-1]['x1']<2:groups[-1].append(c)
   else:groups.append([c])
  refs=[]
  for g in groups:
   num=''.join(c['text'] for c in g);key=callmap.get(num,f'p{n:03}-{num}');callmap[num]=key;refs.append(key);g[0]['text']=f'[^{key}]'
   for c in g:c['top']+=3.2;c['bottom']+=3.2
   for c in g[1:]:c['text']=''
  lines=pdfplumber.utils.chars_to_textmap(chars,x_tolerance=1,y_tolerance=3.5).extract_text_lines(return_chars=True) if chars else []
  out=[];buf=[];kind='body';newdefs=[];base=min((l['x0'] for l in lines if 50<l['x0']<78),default=60)
  def flush():
   if buf:out.append(('> ' if kind=='quote' else '')+clean(' '.join(buf)));buf.clear()
  for l in lines:
   text=clean(l['text'].strip())
   if not text:continue
   fs=statistics.median([c['size'] for c in l['chars'] if c['text'].strip()])
   if prose and text in ['Notes','Note']:flush();note_mode=True;out.append('## Notes');continue
   if note_mode:
    m=re.match(r'^(\d{1,3})\.\s*(.*)',text)
    if m and (m[1] in callmap or int(m[1])==len(newdefs)+1):
     last_note=callmap.get(m[1],f'p{n:03}-{m[1]}');notes[last_note]=m[2];newdefs.append(last_note)
    elif last_note:notes[last_note]+=' '+text
    else:warnings.append(dict(page=n,unassigned_note=text))
    continue
   if prose and fs>10.7:flush();out.append(('### ' if fs<13 else '## ')+text);continue
   nk='quote' if prose and 9.6<fs<10 else 'body'
   if nk!=kind:flush();kind=nk
   elif prose and kind=='body' and base+7<l['x0']<base+16:flush()
   elif not prose:flush()
   buf.append(text)
  flush();text='\n\n'.join(out);refs=[k for k in refs if f'[^{k}]' in text]
  folio=None
  for line in pg.extract_text_lines(x_tolerance=1,y_tolerance=3):
   z=line['text'].strip()
   if line['top']>pg.height*.85 and re.fullmatch(r'(?:\d\s*){1,3}|[ivxlcdm]+',z):folio=z.replace(' ','')
  orig=str(n-15) if n>=16 else folio
  pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
  if pics and n not in image_pages:image_pages.append(n)
  pages.append(dict(pdf_page=n,original_page=orig,printed_folio=folio,original_page_inferred=bool(n>=16 and not folio),section_id=sid,text=text,refs=refs,notes_started=newdefs,images=n in image_pages))
  pg.close()
  if n%100==0:print('Extracted',n,flush=True)
allrefs={k for p in pages for k in p['refs']};issues=dict(unmatched_references=sorted(allrefs-set(notes)),unmatched_definitions=sorted(set(notes)-allrefs))
for s in chapters+other:
 sub=pages[s['pdf_start']-1:s['pdf_end']];s['source_notes']=sum(len(p['notes_started']) for p in sub)
 s['english_words_approx']=len(re.findall(r'\b[A-Za-z][A-Za-z’\'-]*\b',' '.join(p['text'] for p in sub)))
 s['conversion_issues']={k:[x for x in v if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,v in issues.items()}
d=dict(scope='第七卷；由当前代理逐章翻译，沿用前六卷术语',source_pdf=SOURCE.name,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=len(reader.pages),source_publication_year=2006,editor='斯图尔特·J.布朗、蒂莫西·塔克特',translation_status='in_progress',proofreading_status='pending',pdf_status='pending',chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=sorted(image_pages),extraction_warnings=warnings)
for path,val in [(R/'翻译进度.json',d),(R/'卷七结构.json',bookmarks),(ROOT/'data/volume7/pages.json',pages),(ROOT/'data/volume7/notes.json',notes)]:path.write_text(json.dumps(val,ensure_ascii=False,indent=2),encoding='utf8')
print('Converted',len(pages),'pages;',len(notes),'notes; issues',issues,'warnings',len(warnings),flush=True)
PDTOPPM = poppler_tool('pdftoppm')
for n in sorted(image_pages):
 subprocess.run([str(PDTOPPM),'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(A/f'pdf-{n:03}')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
