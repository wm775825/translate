from pathlib import Path
from environment import poppler_tool, require_uninitialized
import copy, json, re, hashlib, statistics, subprocess, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第四卷')

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / '第四卷'
SOURCE = ROOT / '04 西欧基督教.pdf'
PDTOPPM = poppler_tool('pdftoppm')
if (R / '翻译进度.json').exists():
    old=json.loads((R/'翻译进度.json').read_text(encoding='utf-8'))
    if any(x['status']!='pending' for x in old['chapters']+old['other_sections']):
        raise SystemExit('Refusing to reset translated content.')
R.mkdir(exist_ok=True)
reader = PdfReader(SOURCE)
titles = [
 '教士的贞洁与重整秩序的世界', '罗马主教（1100—1300年）', '宗教贫穷与对完美的追求',
 '修道会与其他修会（约1100—约1350年）', '神学框架', '法律基础', '物质支持之一：堂区',
 '物质支持之二：修会', '圣言及其传播', '基督徒与犹太人', '基督教世界与伊斯兰教',
 '基督徒与异端', '女人与男人', '天堂、地狱与炼狱（1100—1500年）', '圣事生活',
 '宗教声景：礼仪与音乐', '图像及其用途', '玛利亚', '神秘主义与超越',
 '宗教生活的边缘：隐修士、独居修士、悔罪者、第三会会士、贝居安女子与贝格哈德男子',
 '圣徒与朝圣：新与旧', '十字军与征服', '镇压与权力', '信仰与知识人之一',
 '信仰与知识人之二', '通过阅读、写作与榜样获得力量：新虔敬运动', '魔鬼与基督徒共同体',
 '威克里夫主义与罗拉德派', '修会的严规改革', '公共纯洁与纪律：国家与宗教更新',
 '十五世纪的《圣经》'
]
bookmarks = []
def walk(xs, depth=0):
    for x in xs:
        if isinstance(x, list):
            walk(x, depth + 1)
        else:
            bookmarks.append(dict(title=x.title, pdf_start=reader.get_destination_page_number(x)+1, depth=depth))
walk(reader.outline)
chapters = []
for b in bookmarks:
    m = re.match(r'^(\d+)\.\s*(.*)', b['title'])
    if m:
        n = int(m[1])
        chapters.append(dict(chapter=n, title=m[2], title_zh=titles[n-1], pdf_start=b['pdf_start']))
for i, c in enumerate(chapters):
    c['pdf_end'] = chapters[i+1]['pdf_start']-1 if i+1 < len(chapters) else 513
    dividers = [n for n in [29,93,153,237,329,373,425] if c['pdf_start'] < n <= c['pdf_end']]
    if dividers:
        c['pdf_end'] = min(dividers)-1
    c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',
             chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md', status='pending')
other = [
 dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=20),
 dict(key='introduction',title_zh='引言',pdf_start=21,pdf_end=28),
 dict(key='part1',title_zh='第一编 制度与变革（1100—1200年）',pdf_start=29,pdf_end=30),
 dict(key='part2',title_zh='第二编 基督教世界的塑造（1200—1300年）',pdf_start=93,pdf_end=94),
 dict(key='part3',title_zh='第三编 边界的建立',pdf_start=153,pdf_end=154),
 dict(key='part4',title_zh='第四编 基督教世界的形态',pdf_start=237,pdf_end=238),
 dict(key='part5',title_zh='第五编 运动中的基督徒生活',pdf_start=329,pdf_end=330),
 dict(key='part6',title_zh='第六编 基督教社会面临的挑战',pdf_start=373,pdf_end=374),
 dict(key='part7',title_zh='第七编 改革与更新',pdf_start=425,pdf_end=426),
 dict(key='bibliography',title_zh='参考书目选编',pdf_start=514,pdf_end=576),
 dict(key='index',title_zh='索引',pdf_start=577,pdf_end=597),
]
for s in other:
    s.update(english_file=s['title_zh']+'（英文）.md', chinese_file=s['title_zh']+'（中文）.md',status='pending')

def clean(s):
    for a,b in {'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'}.items():
        s=s.replace(a,b)
    return unicodedata.normalize('NFC',re.sub(r'\s+([,.;:!?])',r'\1',s))

pages=[]; note_defs={}; all_refs=[]; image_pages=[]; last_note=None; note_counters={}
with pdfplumber.open(SOURCE) as pdf:
    for num,pg in enumerate(pdf.pages,1):
        chapter=next((c for c in chapters if c['pdf_start']<=num<=c['pdf_end']),None)
        section=chapter or next((s for s in other if s['pdf_start']<=num<=s['pdf_end']),None)
        section_id=('ch'+str(chapter['chapter'])) if chapter else (section['key'] if section else 'unassigned')
        is_prose=bool(chapter) or section_id in ['introduction','conclusion']
        bottom=pg.crop((0,775,pg.width,pg.height)).extract_text() if pg.height>775 else ''
        folio=re.search(r'^\s*(\d{1,3}|[ivxlcdm]+)\s*$',bottom or '',re.M)
        original_page=folio.group(1) if folio else None
        bodychars=[];notechars=[]
        note_candidates=[c for c in pg.chars if abs(c['size']-11.65)<.12 and c['top']>49] if is_prose else []
        note_top=min((c['top'] for c in note_candidates),default=999)
        for ch in pg.chars:
            if num>=30 and (ch['top']<49 or ch['top']>770):
                continue
            cc=copy.copy(ch)
            if is_prose and ch['top']>=note_top-1 and ch['size']<12.1:
                if ch['size']<9.1 and ch['text'].isdigit():
                    cc['text']=ch['text'].translate(str.maketrans('0123456789','⁰¹²³⁴⁵⁶⁷⁸⁹'))
                notechars.append(cc)
            else:
                bodychars.append(cc)
        refs=[]
        if is_prose:
            supers=[c for c in bodychars if 8.5<c['size']<10.1 and re.fullmatch(r'\d',c['text'])]
            groups=[]
            for ch in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
                if groups and abs(groups[-1][-1]['top']-ch['top'])<1 and -.2<=ch['x0']-groups[-1][-1]['x1']<2:
                    groups[-1].append(ch)
                else:
                    groups.append([ch])
            for g in groups:
                number=''.join(ch['text'] for ch in g);key=f'p{num:03}-{number}'
                refs.append(key);g[0]['text']=f'[^{key}]'
                for ch in g[1:]: ch['text']=''
        lines=pdfplumber.utils.chars_to_textmap(bodychars,x_tolerance=1,y_tolerance=6).extract_text_lines(return_chars=True) if bodychars else []
        out=[];buf=[];base=min((l['x0'] for l in lines if 70<l['x0']<110),default=86)
        kind='body'
        def flush():
            if buf:
                s=re.sub(r'([A-Za-z])-\s+([a-z])',r'\1\2',' '.join(buf))
                out.append(('> ' if kind=='quote' else '')+clean(s));buf.clear()
        for l in lines:
            s=l['text'].strip()
            if not s:continue
            sizes=[c['size'] for c in l['chars'] if c['text'].strip() and c['size']>10.2]
            fs=statistics.median(sizes) if sizes else 0
            if fs>15.5:
                flush()
                if len(s.split())>4 and sum(len(t)==1 for t in s.split())/len(s.split())>.65:s=s.replace(' ','')
                out.append('### '+clean(s));continue
            nextkind='quote' if 12.9<fs<13.6 else 'body'
            if nextkind!=kind:
                flush();kind=nextkind
            elif kind=='body' and base+10<l['x0']<base+25:
                flush()
            buf.append(s)
        flush()
        footlines=pdfplumber.utils.chars_to_textmap(notechars,x_tolerance=1,y_tolerance=5).extract_text_lines(return_chars=True) if notechars else []
        newdefs=[]
        for l in footlines:
            s=l['text'].strip();m=re.match(r'^(\d{1,3}|\*)\s+(.*)',s)
            if m and (m[1]=='*' or int(m[1])==note_counters.get(section_id,0)+1):
                last_note=f'p{num:03}-'+('star' if m[1]=='*' else m[1]);note_defs[last_note]=clean(m[2]);newdefs.append(last_note)
                if m[1]!='*':note_counters[section_id]=int(m[1])
            elif last_note:
                before=note_defs[last_note]
                note_defs[last_note]=before[:-1]+clean(s) if before.endswith('-') and re.match('[a-z]',s) else before+' '+clean(s)
            else:
                out.append('> 未归属的脚注行：'+s)
        pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
        if pics or num in [1,6,17,18,19,20]:image_pages.append(num)
        page_text='\n\n'.join(out)
        page_text=re.sub(r'\b(k?m)\[\^p\d+-2\]',r'\1²',page_text)
        if num==31 and 'p031-star' in newdefs:
            page_text=page_text.replace('Clerical purity and the re-ordered world','Clerical purity and the re-ordered world[^p031-star]');refs.append('p031-star')
        refs=[k for k in refs if f'[^{k}]' in page_text]
        pages.append(dict(pdf_page=num,original_page=original_page,section_id=section_id,text=page_text,refs=refs,notes_started=newdefs,images=bool(pics)))
        all_refs+=refs
        pg.close()
        if num%100==0: print('Extracted',num,flush=True)

assert len(pages)==597
issues=dict(unmatched_references=sorted(set(all_refs)-set(note_defs)),unmatched_definitions=sorted(set(note_defs)-set(all_refs)))
def page_md(p):
    n=p['pdf_page']
    s=f'<a id="pdf-{n:03}"></a>\n<!-- PDF page {n}; original page {p["original_page"] or "unnumbered"} -->\n\n'+p['text']+'\n'
    if n in image_pages:s+=f'\n![原书PDF第{n}页图像](assets/pdf-{n:03}.png)\n'
    if p['notes_started']:s+='\n'+'\n\n'.join(f'[^{k}]: {note_defs[k]}' for k in p['notes_started'])+'\n'
    return s
toc='\n'.join(f'- [{b["title"]}](#pdf-{b["pdf_start"]:03})' for b in bookmarks)
full='# 剑桥基督教史 第四卷：西欧基督教（约1100—约1500年）\n\n## 英文转换底稿\n\n保留全部597页的页面锚点。页码按原书页脚记录；正文印刷页码从PDF第21页的第1页起。图像保留原页，地图文字将在卷首资料翻译中另行列出。\n\n'+toc+'\n\n'
full+='\n\n---\n\n'.join(page_md(p) for p in pages)
(R/'04 西欧基督教（英文全文）.md').write_text(full,encoding='utf-8')
for s in chapters+other:
    chunk='\n\n'.join(page_md(p) for p in pages[s['pdf_start']-1:s['pdf_end']])
    (R/s['english_file']).write_text('# '+s['title_zh']+'：英文转换底稿\n\n'+chunk,encoding='utf-8')
    s['english_words_approx']=len(re.findall(r"\b[A-Za-z][A-Za-z’'-]*\b",chunk))
    s['source_notes']=sum(len(p['notes_started']) for p in pages[s['pdf_start']-1:s['pdf_end']])
    s['conversion_issues']={k:[x for x in v if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,v in issues.items()}
d=dict(scope='第四卷全书；当前代理逐章翻译，沿用前三卷规范',source_pdf=SOURCE.name,
       source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=597,source_publication_year=2009,
       translation_status='in_progress',chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=image_pages)
(R/'翻译进度.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'卷四结构.json').write_text(json.dumps(bookmarks,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume4/pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume4/notes.json').write_text(json.dumps(note_defs,ensure_ascii=False,indent=2),encoding='utf-8')
norms=(ROOT/'第三卷/翻译规范.md').read_text(encoding='utf-8-sig')
norms=norms.replace('# 第三卷翻译规范（继承前两卷统一译名）','# 第四卷翻译规范（继承前三卷统一译名）').replace('本卷原书出版语境为 2008 年','本卷原书出版语境为 2009 年')
norms+='\n\n## 第四卷新增约定\n\n- 原书2009年出版；保留作者当时的研究视野和时间措辞。前述第三卷专用约定只适用于相应卷次。\n- Clerical purity 在第一章论题中译为“教士的贞洁”；continence 译为“禁欲”，celibacy 译为“独身”，按语境说明两者差别。\n- religious orders：修会；monastic orders：修道会；cleric：教士；secular priest：在俗司祭。\n- Devotio moderna：新虔敬运动；Lollards：罗拉德派；Wyclif：威克里夫。\n- 第一章原书页脚的星号题注在译文中附于章题，内容完整保留。\n- 英文底稿为自动转换结果；未译部分的分栏、图像文字、特殊字符和脚注仍须逐章核对。\n'
(R/'翻译规范.md').write_text(norms,encoding='utf-8')
print('Converted',len(pages),'pages;',len(chapters),'chapters;',len(note_defs),'notes; issues', {k:len(v) for k,v in issues.items()},flush=True)
assets=R/'assets';assets.mkdir(exist_ok=True)
for n in image_pages:
    q=assets/f'pdf-{n:03}'
    subprocess.run([PDTOPPM,'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(q)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
print('Rendered',len(image_pages),'source image pages',flush=True)
