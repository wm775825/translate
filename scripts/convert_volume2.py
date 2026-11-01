from pathlib import Path
from environment import poppler_tool, require_uninitialized
import copy,json,re,hashlib,statistics,subprocess,unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第二卷')

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'第二卷';R.mkdir(exist_ok=True)
SOURCE=ROOT/'02 君士坦丁至600年.pdf'
PDTOPPM = poppler_tool('pdftoppm')
reader=PdfReader(SOURCE)
titles=[
 '西方的基督教诸形态','日耳曼与凯尔特的基督教诸形态','希腊世界的基督教诸形态','早期亚洲与东非的基督教诸形态',
 '古代晚期基督徒与犹太人之间的宗教互动（312—640年）','基督教与异教之一：埃及','基督教与异教之二：小亚细亚',
 '基督教与异教之三：意大利','基督教与异教之四：北非','基督徒与异教徒之间的思想论争','基督教与摩尼教',
 '异端学：“异端”与“分裂”的发明','走向基督教文化的界定：古典文学的基督教转化','主教与社会','主教会议与大公会议',
 '教会法的发展','教会、社会与政治权力','论三一','七世纪以前的基督论史','罪与救恩：经验与反思',
 '从安提阿到阿尔勒：处境中的平信徒虔敬','圣徒与圣人','牧养与纪律','性、婚姻与家庭',
 '礼仪与教会年的发展','圣经诠释','禁欲与修道生活之一：东方','禁欲与修道生活之二：西方',
 '艺术与信仰传播：300—600年的基督教艺术与建筑']
chapters=[];bookmarks=[]
def walk(xs,depth=0):
 for x in xs:
  if isinstance(x,list):walk(x,depth+1)
  else:
   bookmarks.append(dict(title=x.title,pdf_start=reader.get_destination_page_number(x)+1,depth=depth))
walk(reader.outline)
for b in bookmarks:
 m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
 if m:
  n=int(m[1]);chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
for i,c in enumerate(chapters):
 c['pdf_end']=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 746
 # Part divider pages belong to the following part rather than the preceding chapter.
 dividers=[b['pdf_start'] for b in bookmarks if b['title'].startswith('Part ') and c['pdf_start']<b['pdf_start']<=c['pdf_end']]
 if dividers:c['pdf_end']=min(dividers)-1
 c['english_file']=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md'
 c['chinese_file']=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md'
 c['status']='pending'

def clean(s):
 s=s.replace('ﬁ','fi').replace('ﬂ','fl').replace('ﬀ','ff').replace('ﬃ','ffi').replace('ﬄ','ffl')
 s=re.sub(r'\s+([,.;:!?])',r'\1',s)
 return unicodedata.normalize('NFC',s)
pages=[];note_defs={};all_refs=[];image_pages=[];last_note=None;note_counters={}
with pdfplumber.open(SOURCE) as pdf:
 for num,pg in enumerate(pdf.pages,1):
  is_chapter=next((c for c in chapters if c['pdf_start']<=num<=c['pdf_end']),None)
  is_prose=22<=num<747
  bodychars=[];notechars=[]
  note_candidates=[c for c in pg.chars if abs(c['size']-8.5)<.15 and c['top']>200]
  note_top=min((c['top'] for c in note_candidates),default=999)
  # Font sizes, rather than a fixed page coordinate, identify chapter notes.
  for ch in pg.chars:
   if num>=22 and (ch['top']<49 or ch['top']>580):continue
   if is_prose and note_top<999 and ch['top']>=note_top-1 and ch['size']<9.1:
    cc=copy.copy(ch)
    if ch['size']<6.8 and ch['text'].isdigit():cc['text']=ch['text'].translate(str.maketrans('0123456789','⁰¹²³⁴⁵⁶⁷⁸⁹'))
    notechars.append(cc)
   else:bodychars.append(copy.copy(ch))
  refs=[]
  if is_chapter:
   supers=[c for c in bodychars if 6.5<c['size']<7.8 and re.fullmatch(r'\d',c['text'])]
   groups=[]
   for ch in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
    if groups and abs(groups[-1][-1]['top']-ch['top'])<1 and -.2<=ch['x0']-groups[-1][-1]['x1']<2:
     groups[-1].append(ch)
    else:groups.append([ch])
   for g in groups:
    number=''.join(ch['text'] for ch in g);key=f'p{num:03}-{number}'
    refs.append(key);g[0]['text']=f'[^{key}]'
    for ch in g[1:]:ch['text']=''
  lines=pdfplumber.utils.chars_to_textmap(bodychars,x_tolerance=1,y_tolerance=4).extract_text_lines(return_chars=True) if bodychars else []
  out=[];buf=[];base=min((l['x0'] for l in lines if l['x0']<100),default=60)
  def flush():
   if buf:
    text=' '.join(buf);text=re.sub(r'([A-Za-z])-\s+([a-z])',r'\1\2',text)
    out.append(clean(text));buf.clear()
  for l in lines:
   text=l['text'].strip()
   if not text:continue
   sizes=[c['size'] for c in l['chars'] if c['text'].strip() and c['size']>8]
   fs=statistics.median(sizes) if sizes else 0
   if fs>11.3:
    flush()
    if len(text.split())>4 and sum(len(t)==1 for t in text.split())/len(text.split())>.65:text=text.replace(' ','')
    out.append('### '+clean(text))
   elif l['x0']>base+6 and l['x0']<base+18:
    flush();buf.append(text)
   else:buf.append(text)
  flush()
  footlines=pdfplumber.utils.chars_to_textmap(notechars,x_tolerance=1,y_tolerance=3).extract_text_lines(return_chars=True) if notechars else []
  newdefs=[]
  for l in footlines:
   text=l['text'].strip();m=re.match(r'^(\d{1,3})\s+(.*)',text)
   chapter_id=is_chapter['chapter'] if is_chapter else 0
   if m and int(m[1])==note_counters.get(chapter_id,0)+1:
    last_note=f'p{num:03}-{m[1]}'
    note_defs[last_note]=clean(m[2]);newdefs.append(last_note)
    note_counters[chapter_id]=int(m[1])
   elif last_note:
    before=note_defs[last_note]
    note_defs[last_note]=before[:-1]+clean(text) if before.endswith('-') and re.match('[a-z]',text) else before+' '+clean(text)
   else:out.append('> 未归属的脚注行：'+text)
  pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
  if pics or num in [1,6,17,19,20,21]:image_pages.append(num)
  page_text='\n\n'.join(out)
  page_text=re.sub(r'\b(k?m)\[\^p\d+-2\]',r'\1²',page_text)
  refs=[key for key in refs if f'[^{key}]' in page_text]
  pages.append(dict(pdf_page=num,original_page=str(num-21) if num>=22 else None,
                    text=page_text,refs=refs,notes_started=newdefs,images=bool(pics)))
  all_refs+=refs
  if num%100==0:print('Extracted',num,flush=True)

assert len(pages)==781
refsset=set(all_refs);defsset=set(note_defs)
issues=dict(unmatched_references=sorted(refsset-defsset),unmatched_definitions=sorted(defsset-refsset))
def page_md(p):
 n=p['pdf_page'];s=f'<a id="pdf-{n:03}"></a>\n<!-- PDF page {n}; original page {p["original_page"] or "front matter"} -->\n\n'
 s+=p['text']+'\n'
 if n in image_pages:s+=f'\n![原书PDF第{n}页图像](assets/pdf-{n:03}.png)\n'
 if p['notes_started']:s+='\n'+'\n\n'.join(f'[^{k}]: {note_defs[k]}' for k in p['notes_started'])+'\n'
 return s
toc='\n'.join(f'- [{b["title"]}](#pdf-{b["pdf_start"]:03})' for b in bookmarks)
full='# 剑桥基督教史 第二卷：君士坦丁至约600年\n\n## 英文转换底稿\n\n保留全部781页页面锚点。该文件为可检索的转换底稿，段落、特殊字形及脚注将在逐章翻译时对照原PDF复核。\n\n'+toc+'\n\n'
full+='\n\n---\n\n'.join(page_md(p) for p in pages)
(R/'02 君士坦丁至600年（英文全文）.md').write_text(full,encoding='utf-8')
for c in chapters:
 chunk='\n\n'.join(page_md(p) for p in pages[c['pdf_start']-1:c['pdf_end']])
 (R/c['english_file']).write_text(f'# 第{c["chapter"]:02}章英文原文：{c["title"]}\n\n'+chunk,encoding='utf-8')
 c['english_words_approx']=len(re.findall(r"\b[A-Za-z][A-Za-z’'-]*\b",chunk))
 c['source_notes']=sum(len(p['notes_started']) for p in pages[c['pdf_start']-1:c['pdf_end']])
 c['conversion_issues']={k:[x for x in v if c['pdf_start']<=int(x[1:4])<=c['pdf_end']] for k,v in issues.items()}
intro=dict(key='introduction',title_zh='引言',pdf_start=22,pdf_end=27,
           english_file='引言（英文）.md',chinese_file='引言（中文）.md',status='pending')
(R/intro['english_file']).write_text('# 引言英文原文\n\n'+'\n\n'.join(page_md(p) for p in pages[21:27]),encoding='utf-8')
d=dict(scope='第二卷全书；由当前代理逐章翻译，沿用第一卷规范',source_pdf=SOURCE.name,
       source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=781,
       source_publication_year=2007,translation_status='in_progress',chapters=chapters,
       other_sections=[intro],conversion_issues=issues,image_pages=image_pages)
(R/'翻译进度.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'卷二结构.json').write_text(json.dumps(bookmarks,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume2/pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume2/notes.json').write_text(json.dumps(note_defs,ensure_ascii=False,indent=2),encoding='utf-8')
norms=(ROOT/'第一卷/翻译规范.md').read_text(encoding='utf-8-sig').replace('# 第一卷翻译规范','# 第二卷翻译规范（继承第一卷统一译名）').replace('原书写作语境为 2006 年','本卷原书出版语境为 2007 年')
norms+='\n\n## 第二卷新增约定\n\n- Christianities按语境译为“基督教诸形态”，保留其复数所强调的地域与群体多样性。\n- Homoian：相似派；homoios：相似。须与homoiousios（本质相似）及homoousios（同质）区分。\n- Nicene：尼西亚派／尼西亚信仰，依语境；本卷late antiquity统一译为“古代晚期”。\n'
(R/'翻译规范.md').write_text(norms,encoding='utf-8')
print('Converted',len(pages),'pages;',len(chapters),'chapters;',len(note_defs),'notes; issues', {k:len(v) for k,v in issues.items()},flush=True)
assets=R/'assets';assets.mkdir(exist_ok=True)
for n in image_pages:
 q=assets/f'pdf-{n:03}'
 subprocess.run([PDTOPPM,'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(q)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
print('Rendered',len(image_pages),'source image pages',flush=True)
