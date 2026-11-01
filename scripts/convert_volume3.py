from pathlib import Path
from environment import poppler_tool, require_uninitialized
import copy, json, re, hashlib, statistics, subprocess, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第三卷')

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / '第三卷'
SOURCE = ROOT / '03 中世纪早期基督教.pdf'
PDTOPPM = poppler_tool('pdftoppm')
if (R / '翻译进度.json').exists():
    raise SystemExit('Conversion already exists; refusing to reset translation progress.')
R.mkdir(exist_ok=True)
reader = PdfReader(SOURCE)
titles = [
    '罗马晚期的基督教诸形态', '拜占庭正教的形成（600—1095年）',
    '帝国之外之一：从波斯征服到突厥征服的东方基督教诸形态（604—1071年）',
    '帝国之外之二：凯尔特诸民族的基督教诸形态', '日耳曼的基督教诸形态',
    '斯拉夫的基督教诸形态（800—1100年）', '基督徒与犹太人',
    '地中海边疆：基督教与伊斯兰教的相遇（600—1050年）', '穆斯林统治下的基督徒',
    '拉丁基督徒与希腊基督徒', '北方边疆：基督教与异教的相遇',
    '作为制度的基督教会', '禁欲及其制度', '法律及其运用', '财产问题',
    '改革的观念与实践', '景观中的教堂', '出生与死亡', '罪的补救', '疾病与医治',
    '性别与身体', '拉丁基督教中的祭献、馈赠与祈祷', '礼仪的施行', '上帝的异象',
    '正统与偏离', '理解《圣经》', '中世纪拜占庭的基督教书籍', '圣徒及其崇敬', '末后之事'
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
    c['pdf_end'] = chapters[i+1]['pdf_start']-1 if i+1 < len(chapters) else 652
    dividers = [b['pdf_start'] for b in bookmarks if b['title'].startswith('Part ') and c['pdf_start'] < b['pdf_start'] <= c['pdf_end']]
    if dividers:
        c['pdf_end'] = min(dividers)-1
    c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',
             chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md', status='pending')
other = [
    dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=29),
    dict(key='introduction',title_zh='引言：约600年的基督教世界',pdf_start=30,pdf_end=47),
    dict(key='part1',title_zh='第一编 基础：民族、地域与传统',pdf_start=48,pdf_end=49),
    dict(key='part2',title_zh='第二编 交锋中的基督教',pdf_start=186,pdf_end=187),
    dict(key='part3',title_zh='第三编 社会与政治秩序中的基督教',pdf_start=276,pdf_end=277),
    dict(key='part4',title_zh='第四编 作为生活经验的基督教',pdf_start=410,pdf_end=411),
    dict(key='part5',title_zh='第五编 基督教：书籍与观念',pdf_start=518,pdf_end=518),
    dict(key='conclusion',title_zh='结语：约1100年的基督教世界',pdf_start=653,pdf_end=671),
    dict(key='bibliography',title_zh='参考文献',pdf_start=672,pdf_end=830),
    dict(key='index',title_zh='索引',pdf_start=831,pdf_end=874),
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
        bottom=pg.crop((0,575,pg.width,pg.height)).extract_text() if pg.height>575 else ''
        folio=re.search(r'^\s*(\d{1,3}|[ivxlcdm]+)\s*$',bottom or '',re.M)
        original_page=folio.group(1) if folio else None
        bodychars=[];notechars=[]
        note_candidates=[c for c in pg.chars if abs(c['size']-8.47)<.12 and c['top']>49] if is_prose else []
        note_top=min((c['top'] for c in note_candidates),default=999)
        for ch in pg.chars:
            if num>=30 and (ch['top']<49 or ch['top']>580):
                continue
            cc=copy.copy(ch)
            if is_prose and ch['top']>=note_top-1 and ch['size']<9.1:
                if ch['size']<6.8 and ch['text'].isdigit():
                    cc['text']=ch['text'].translate(str.maketrans('0123456789','⁰¹²³⁴⁵⁶⁷⁸⁹'))
                notechars.append(cc)
            else:
                bodychars.append(cc)
        refs=[]
        if is_prose:
            supers=[c for c in bodychars if 6.5<c['size']<8.1 and re.fullmatch(r'\d',c['text'])]
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
        lines=pdfplumber.utils.chars_to_textmap(bodychars,x_tolerance=1,y_tolerance=4).extract_text_lines(return_chars=True) if bodychars else []
        out=[];buf=[];base=min((l['x0'] for l in lines if l['x0']<100),default=60)
        def flush():
            if buf:
                s=re.sub(r'([A-Za-z])-\s+([a-z])',r'\1\2',' '.join(buf))
                out.append(clean(s));buf.clear()
        for l in lines:
            s=l['text'].strip()
            if not s:continue
            sizes=[c['size'] for c in l['chars'] if c['text'].strip() and c['size']>8]
            fs=statistics.median(sizes) if sizes else 0
            if fs>11.3:
                flush()
                if len(s.split())>4 and sum(len(t)==1 for t in s.split())/len(s.split())>.65:s=s.replace(' ','')
                out.append('### '+clean(s))
            elif base+6<l['x0']<base+18:
                flush();buf.append(s)
            else:buf.append(s)
        flush()
        footlines=pdfplumber.utils.chars_to_textmap(notechars,x_tolerance=1,y_tolerance=3).extract_text_lines(return_chars=True) if notechars else []
        newdefs=[]
        for l in footlines:
            s=l['text'].strip();m=re.match(r'^(\d{1,3})\s+(.*)',s)
            if m and int(m[1])==note_counters.get(section_id,0)+1:
                last_note=f'p{num:03}-{m[1]}';note_defs[last_note]=clean(m[2]);newdefs.append(last_note)
                note_counters[section_id]=int(m[1])
            elif last_note:
                before=note_defs[last_note]
                note_defs[last_note]=before[:-1]+clean(s) if before.endswith('-') and re.match('[a-z]',s) else before+' '+clean(s)
            else:
                out.append('> 未归属的脚注行：'+s)
        pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
        if pics or num in [1,6,24,25,26,27,28,29]:image_pages.append(num)
        page_text='\n\n'.join(out)
        page_text=re.sub(r'\b(k?m)\[\^p\d+-2\]',r'\1²',page_text)
        refs=[k for k in refs if f'[^{k}]' in page_text]
        pages.append(dict(pdf_page=num,original_page=original_page,section_id=section_id,text=page_text,refs=refs,notes_started=newdefs,images=bool(pics)))
        all_refs+=refs
        pg.close()
        if num%100==0: print('Extracted',num,flush=True)

assert len(pages)==876
issues=dict(unmatched_references=sorted(set(all_refs)-set(note_defs)),unmatched_definitions=sorted(set(note_defs)-set(all_refs)))
def page_md(p):
    n=p['pdf_page']
    s=f'<a id="pdf-{n:03}"></a>\n<!-- PDF page {n}; original page {p["original_page"] or "unnumbered"} -->\n\n'+p['text']+'\n'
    if n in image_pages:s+=f'\n![原书PDF第{n}页图像](assets/pdf-{n:03}.png)\n'
    if p['notes_started']:s+='\n'+'\n\n'.join(f'[^{k}]: {note_defs[k]}' for k in p['notes_started'])+'\n'
    return s
toc='\n'.join(f'- [{b["title"]}](#pdf-{b["pdf_start"]:03})' for b in bookmarks)
full='# 剑桥基督教史 第三卷：中世纪早期基督教诸形态（约600—约1100年）\n\n## 英文转换底稿\n\n保留全部876页的页面锚点。页码按原书页脚记录；第五编前原文件少一张空白页，故不采用固定页码偏移。图像保留原页，地图文字将在卷首资料翻译中另行列出。\n\n'+toc+'\n\n'
full+='\n\n---\n\n'.join(page_md(p) for p in pages)
(R/'03 中世纪早期基督教（英文全文）.md').write_text(full,encoding='utf-8')
for s in chapters+other:
    chunk='\n\n'.join(page_md(p) for p in pages[s['pdf_start']-1:s['pdf_end']])
    (R/s['english_file']).write_text('# '+s['title_zh']+'：英文转换底稿\n\n'+chunk,encoding='utf-8')
    s['english_words_approx']=len(re.findall(r"\b[A-Za-z][A-Za-z’'-]*\b",chunk))
    s['source_notes']=sum(len(p['notes_started']) for p in pages[s['pdf_start']-1:s['pdf_end']])
    s['conversion_issues']={k:[x for x in v if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,v in issues.items()}
d=dict(scope='第三卷全书；当前代理逐章翻译，沿用前两卷规范',source_pdf=SOURCE.name,
       source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=876,source_publication_year=2008,
       translation_status='in_progress',chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=image_pages)
(R/'翻译进度.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'卷三结构.json').write_text(json.dumps(bookmarks,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume3/pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/volume3/notes.json').write_text(json.dumps(note_defs,ensure_ascii=False,indent=2),encoding='utf-8')
norms=(ROOT/'第二卷/翻译规范.md').read_text(encoding='utf-8-sig')
norms=norms.replace('# 第二卷翻译规范（继承第一卷统一译名）','# 第三卷翻译规范（继承前两卷统一译名）').replace('本卷原书出版语境为 2007 年','本卷原书出版语境为 2008 年')
norms+='\n\n## 第三卷新增约定\n\n- 原书2008年出版，保留作者当时的历史判断、研究视野和时间措辞。\n- Christendom：基督教世界。书名中的 Christianities 译为“基督教诸形态”。\n- Byzantine Orthodoxy：拜占庭正教；Eastern Christianities：东方基督教诸形态，依上下文区分。\n- 年代、引文、正文论证与解释性脚注完整翻译；参考文献保留作者、原文题名和定位信息。\n- 本卷脚注按各章（以及引言、结语）独立编号，标识保留PDF物理页码以便回查。\n- 英文底稿只完成文字转换，未校对部分不可视为可靠的定本。译文仅在已完成相应原文核对后标为完成。\n'
(R/'翻译规范.md').write_text(norms,encoding='utf-8')
print('Converted',len(pages),'pages;',len(chapters),'chapters;',len(note_defs),'notes; issues', {k:len(v) for k,v in issues.items()},flush=True)
assets=R/'assets';assets.mkdir(exist_ok=True)
for n in image_pages:
    q=assets/f'pdf-{n:03}'
    subprocess.run([PDTOPPM,'-f',str(n),'-l',str(n),'-scale-to','1800','-singlefile','-png',str(SOURCE),str(q)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
print('Rendered',len(image_pages),'source image pages',flush=True)
