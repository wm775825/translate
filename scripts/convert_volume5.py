from pathlib import Path
from environment import poppler_tool, require_uninitialized
import copy, json, re, hashlib, statistics, subprocess, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第五卷')

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / '第五卷'
SOURCE = ROOT / '05 东方基督教.pdf'
TMP = ROOT / 'data/volume5'
PDTOPPM = poppler_tool('pdftoppm')
if (R / '翻译进度.json').exists():
    raise SystemExit('Existing volume 5 project; use its continuation tools rather than reset it.')
R.mkdir(exist_ok=True); TMP.mkdir(exist_ok=True)
reader = PdfReader(SOURCE)
titles = [
 '拜占庭共同体（1000—1550年）', '拜占庭与西方（1204—1453年）',
 '中世纪拜占庭的平信徒虔敬文化（1054—1453年）', '静修主义的兴起',
 '拜占庭帝国晚期的艺术与礼仪', '阿索斯山与奥斯曼人（约1350—1550年）',
 '被囚禁的大教会（1453—1586年）', '正教与西方：从宗教改革到启蒙运动',
 '巴尔斯基与正教共同体', '法国大革命的遗产：正教与民族主义',
 '俄国的虔敬与正教文化（1380—1589年）', '俄国的艺术与礼仪：鲁布廖夫及其继承者',
 '反宗教改革时代俄国与乌克兰的东正教', '俄罗斯帝国时期的俄罗斯东正教会（1721—1917年）',
 '从彼得大帝到1917年的俄国虔敬与文化',
 '东方基督教诸形态（十一至十四世纪）：科普特人、麦勒凯派、涅斯托里乌斯派与雅各派',
 '十字军时代的亚美尼亚人（1050—1350年）', '教会与离散：亚美尼亚人的个案',
 '教会与民族：埃塞俄比亚正统合一教会（十三至二十世纪）',
 '现代埃及的科普特基督教', '现代中东的叙利亚传统基督教',
 '俄国流亡者的离散问题', '东正教会与共产主义', '现代灵修与东正教会'
]
bookmarks=[]
def walk(xs,depth=0):
    for x in xs:
        if isinstance(x,list): walk(x,depth+1)
        else: bookmarks.append(dict(title=x.title,pdf_start=reader.get_destination_page_number(x)+1,depth=depth))
walk(reader.outline)
chapters=[]
for b in bookmarks:
    m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
    if m:
        n=int(m[1]);chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
dividers=[22,272,392,558]
for i,c in enumerate(chapters):
    c['pdf_end']=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 620
    cuts=[n for n in dividers if c['pdf_start']<n<=c['pdf_end']]
    if cuts:c['pdf_end']=min(cuts)-1
    c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',
             chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md',status='pending')
other=[
 dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=16),
 dict(key='foreword',title_zh='前言',pdf_start=17,pdf_end=19),
 dict(key='abbreviations',title_zh='缩略语',pdf_start=20,pdf_end=21),
 dict(key='part1',title_zh='第一编 普世牧首区',pdf_start=22,pdf_end=23),
 dict(key='part2',title_zh='第二编 俄罗斯教会',pdf_start=272,pdf_end=273),
 dict(key='part3',title_zh='第三编 东方基督教诸形态',pdf_start=392,pdf_end=393),
 dict(key='part4',title_zh='第四编 现代世界',pdf_start=558,pdf_end=559),
 dict(key='bibliography',title_zh='参考书目选编',pdf_start=621,pdf_end=699),
 dict(key='index',title_zh='索引',pdf_start=700,pdf_end=745),
]
for s in other:s.update(english_file=s['title_zh']+'（英文）.md',chinese_file=s['title_zh']+'（中文）.md',status='pending')
assert sorted(n for s in chapters+other for n in range(s['pdf_start'],s['pdf_end']+1))==list(range(1,746))

def clean(s):
    for a,b in {'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'}.items():s=s.replace(a,b)
    # Restore individually positioned Latin accent glyphs where their order is unambiguous.
    for mark,comb in [('´','\u0301'),('`','\u0300'),('¨','\u0308'),('˜','\u0303')]:
        s=re.sub(r'([A-Za-z])'+re.escape(mark),lambda m:m[1]+comb,s)
    return unicodedata.normalize('NFC',re.sub(r'\s+([,.;:!?])',r'\1',s))

map_pages=[25,34,232,275,395,426,479]
map_exclusions={25:(64,70,374,453),34:(64,85,374,612)}
pages=[];note_defs={};all_refs=[];image_pages=[];last_note=None;last_section=None;note_counters={};warnings=[]
with pdfplumber.open(SOURCE) as pdf:
    for num,pg in enumerate(pdf.pages,1):
        chapter=next((c for c in chapters if c['pdf_start']<=num<=c['pdf_end']),None)
        section=chapter or next(s for s in other if s['pdf_start']<=num<=s['pdf_end'])
        sid='ch'+str(chapter['chapter']) if chapter else section['key']
        if sid!=last_section:last_note=None;last_section=sid
        prose=bool(chapter) or sid=='foreword'
        if pg.height<615:
            warnings.append(dict(page=num,review='Landscape/rotated source page: preserve complete raw text and inspect layout before translation.'))
            pages.append(dict(pdf_page=num,original_page=str(num-21),printed_folio=None,original_page_inferred=True,
                section_id=sid,text=clean(pg.extract_text() or ''),refs=[],notes_started=[],images=True))
            image_pages.append(num);pg.close();continue
        folio_text=pg.crop((0,590,pg.width,615)).extract_text() or ''
        folio=re.search(r'^\s*(\d{1,3}|[ivxlcdm]+)\s*$',folio_text,re.M)
        original_page=str(num-21) if num>=22 else (folio[1] if folio else None)
        excluded=map_exclusions.get(num)
        usable=[c for c in pg.chars if c['top']<590 and not (num>=24 and c['top']<65)
                and not (excluded and excluded[0]<=((c['x0']+c['x1'])/2)<=excluded[2] and excluded[1]<=c['top']<=excluded[3])]
        note_candidates=[c for c in usable if abs(c['size']-8.47)<.08 and c['top']>90] if prose else []
        note_top=min((c['top'] for c in note_candidates),default=999)
        bodychars=[];notechars=[]
        for ch in usable:
            cc=copy.copy(ch)
            if prose and ch['top']>=note_top-1 and ch['size']<8.7:notechars.append(cc)
            else:bodychars.append(cc)
        refs=[]
        if prose:
            supers=[c for c in bodychars if 7.1<c['size']<7.7 and re.fullmatch(r'\d',c['text'])]
            groups=[]
            for ch in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
                if groups and abs(groups[-1][-1]['top']-ch['top'])<1 and -.2<=ch['x0']-groups[-1][-1]['x1']<2:groups[-1].append(ch)
                else:groups.append([ch])
            for g in groups:
                k=f'p{num:03}-'+''.join(c['text'] for c in g);refs.append(k);g[0]['text']=f'[^{k}]'
                for ch in g[1:]:ch['text']=''
        lines=pdfplumber.utils.chars_to_textmap(bodychars,x_tolerance=1,y_tolerance=4).extract_text_lines(return_chars=True) if bodychars else []
        out=[];buf=[];base=min((l['x0'] for l in lines if 50<l['x0']<70),default=59);kind='body'
        def flush():
            if buf:
                s=re.sub(r'([A-Za-z])-\s+([a-z])',r'\1\2',' '.join(buf))
                out.append(('> ' if kind=='quote' else '')+clean(s));buf.clear()
        for l in lines:
            s=l['text'].strip()
            if not s:continue
            sizes=[c['size'] for c in l['chars'] if c['text'].strip() and c['size']>8.7]
            fs=statistics.median(sizes) if sizes else 0
            if fs>11.3:
                flush();out.append('### '+clean(s));continue
            nextkind='quote' if 8.8<fs<9.2 else 'body'
            if nextkind!=kind:flush();kind=nextkind
            elif kind=='body' and base+7<l['x0']<base+21:flush()
            buf.append(s)
        flush()
        footlines=pdfplumber.utils.chars_to_textmap(notechars,x_tolerance=1,y_tolerance=3).extract_text_lines(return_chars=True) if notechars else []
        newdefs=[]
        for l in footlines:
            s=l['text'].strip();m=re.match(r'^(\d{1,3}|\*)\s+(.*)',s)
            if m and (m[1]=='*' or int(m[1])==note_counters.get(sid,0)+1):
                last_note=f'p{num:03}-'+('star' if m[1]=='*' else m[1]);note_defs[last_note]=clean(m[2]);newdefs.append(last_note)
                if m[1]!='*':note_counters[sid]=int(m[1])
            elif last_note:
                before=note_defs[last_note];note_defs[last_note]=before[:-1]+clean(s) if before.endswith('-') and re.match('[a-z]',s) else before+' '+clean(s)
            else:warnings.append(dict(page=num,unassigned_note=s))
        pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
        if pics or num in map_pages or num==1:image_pages.append(num)
        page_text='\n\n'.join(out)
        refs=[k for k in refs if f'[^{k}]' in page_text]
        pages.append(dict(pdf_page=num,original_page=original_page,printed_folio=folio[1] if folio else None,
            original_page_inferred=bool(num>=22 and not folio),section_id=sid,text=page_text,refs=refs,notes_started=newdefs,images=bool(pics) or num in map_pages))
        all_refs+=refs;pg.close()
        if num%100==0:print('Extracted',num,flush=True)

issues=dict(unmatched_references=sorted(set(all_refs)-set(note_defs)),unmatched_definitions=sorted(set(note_defs)-set(all_refs)))
def page_md(p):
    n=p['pdf_page'];s=f'<a id="pdf-{n:03}"></a>\n<!-- PDF page {n}; original page {p["original_page"] or "unnumbered"} -->\n\n'+p['text']+'\n'
    if n in image_pages:s+=f'\n![原书PDF第{n}页图像](assets/pdf-{n:03}.png)\n'
    if p['notes_started']:s+='\n'+'\n\n'.join(f'[^{k}]: {note_defs[k]}' for k in p['notes_started'])+'\n'
    return s
toc='\n'.join(f'- [{s["title_zh"]}](#pdf-{s["pdf_start"]:03})' for s in sorted(chapters+other,key=lambda s:s['pdf_start']))
full='# 剑桥基督教史 第五卷：东方基督教\n\n## 英文转换底稿\n\n原书2006年出版。保留全部745页页面锚点；正文原页码=PDF页码减21。未译章节中的分栏、特殊字符、图表与脚注尚须人工核对，不应视为校定英文文本。\n\n'+toc+'\n\n'
full+='\n\n---\n\n'.join(page_md(p) for p in pages)
(R/'05 东方基督教（英文全文）.md').write_text(full,encoding='utf-8')
for s in chapters+other:
    chunk='\n\n'.join(page_md(p) for p in pages[s['pdf_start']-1:s['pdf_end']])
    (R/s['english_file']).write_text('# '+s['title_zh']+'：英文转换底稿\n\n'+chunk,encoding='utf-8')
    s['english_words_approx']=len(re.findall(r"\b[A-Za-z][A-Za-z’'-]*\b",chunk))
    s['source_notes']=sum(len(p['notes_started']) for p in pages[s['pdf_start']-1:s['pdf_end']])
    s['conversion_issues']={k:[x for x in v if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,v in issues.items()}
d=dict(scope='第五卷全书；当前代理逐章翻译，沿用前四卷规范',source_pdf=SOURCE.name,
 source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=745,source_publication_year=2006,
 translation_status='in_progress',chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=image_pages,
 extraction_warnings=warnings,source_discrepancies=[dict(pdf_page=24,description='第一章原目录为1000–1500；章首页及页眉为1000–1550。译文章题依正文。')])
for path,value in [(R/'翻译进度.json',d),(R/'卷五结构.json',bookmarks),(ROOT/'data/volume5/pages.json',pages),(ROOT/'data/volume5/notes.json',note_defs)]:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print('Converted',len(pages),'pages;',len(chapters),'chapters;',len(note_defs),'notes; issues', {k:len(v) for k,v in issues.items()},'warnings',len(warnings),flush=True)
assets=R/'assets';assets.mkdir(exist_ok=True)
for n in image_pages:
    subprocess.run([PDTOPPM,'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(assets/f'pdf-{n:03}')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
with pdfplumber.open(SOURCE) as pdf:
    for n,idx,bbox in [(25,1,(66,74,371,433)),(34,2,(65,90,362,594))]:
        pdf.pages[n-1].crop(bbox).to_image(resolution=240).save(assets/f'map-{idx:02}.png')
print('Rendered',len(image_pages),'source image pages and two chapter 1 map crops',flush=True)
