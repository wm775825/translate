from pathlib import Path
from environment import poppler_tool, require_uninitialized
import collections, copy, hashlib, json, re, statistics, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第九卷')

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'第九卷'; T=ROOT/'data/volume9'; A=R/'assets'
for p in (R,T,A): p.mkdir(exist_ok=True)
assert not (R/'翻译进度.json').exists() or all(x['status']=='pending' for x in (json.loads((R/'翻译进度.json').read_text(encoding='utf8'))['chapters']+json.loads((R/'翻译进度.json').read_text(encoding='utf8'))['other_sections'])), 'Initial extraction only; never reset translated work.'
SOURCE=ROOT/'09 世界基督教（1914-2000）.pdf'
reader=PdfReader(SOURCE)
bookmarks=json.loads((T/'outline.json').read_text(encoding='utf8'))
titles=[
'导论','二十世纪初的基督徒生活','教皇制度','普世教会运动','基督教、殖民主义与传教',
'五旬节运动与灵恩运动','非洲与亚洲的独立教会运动','第一次世界大战','欧洲基督教会与政治（1914—1939年）',
'拉丁美洲（约1914—约1950年）','非洲基督教：从世界大战到非殖民化',
'加勒比与欧洲的非洲离散群体：从奴隶解放前到当代','两次世界大战之间的美国基督教',
'澳大利亚、新西兰与太平洋的基督教会（1914—1970年）','欧洲第二次世界大战中的天主教与新教',
'冷战、美国霸权与基督教民主主义的黄金时代','六十年代的宗教激荡','西方基督教的危机：走向后基督教时代？',
'东欧剧变与后共产主义时代的开端','拉丁美洲基督教的转型（约1950—2000年）',
'宗教与种族主义：围绕种族隔离、“吉姆·克劳”与南非种族隔离制度的斗争','后殖民时代非洲的基督教',
'南亚（1911—2003年）','东南亚的基督教（1914—2000年）','东亚','礼拜仪式','“他者”','财富与贫困',
'男性与女性','基督教与科学','文学与艺术','榜样','二十世纪末的基督徒生活']
dividers=[46,148,470]
chapters=[]
for b in bookmarks:
    m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
    if 'Chapter 20 missing' in b['title']:
        m=re.match(r'^(\d+)\.\s*(.*)', '20. The transformation of Latin American Christianity, c.1950–2000')
    if m:
        n=int(m[1]);chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
for i,c in enumerate(chapters):
    end=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 648
    c['pdf_end']=min([end]+[n-1 for n in dividers if c['pdf_start']<n<=end])
    c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',
             chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md',status='pending')
other=[dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=19),
       *[dict(key=f'part{i+1}',title_zh='第'+['一','二','三'][i]+'编 '+title,pdf_start=n,pdf_end=n+1)
         for i,(n,title) in enumerate(zip(dividers,['制度与运动','变迁的历程','社会与文化影响']))],
       dict(key='bibliography',title_zh='参考书目',pdf_start=649,pdf_end=691),
       dict(key='index',title_zh='索引',pdf_start=692,pdf_end=720)]
for s in other:
    s.update(english_file=s['title_zh']+'（英文）.md',chinese_file=s['title_zh']+'（中文）.md',status='pending')
assert sorted(n for s in chapters+other for n in range(s['pdf_start'],s['pdf_end']+1))==list(range(1,721))

def clean(s):
    for a,b in {'ﬁ':'fi','ﬂ':'fl','ﬀ':'ff','ﬃ':'ffi','ﬄ':'ffl'}.items():s=s.replace(a,b)
    for mark,comb in [('´','\u0301'),('`','\u0300'),('¨','\u0308'),('˜','\u0303'),('ˇ','\u030c'),('˚','\u030a'),('ˆ','\u0302'),('¸','\u0327')]:
        s=re.sub(r'([A-Za-z])'+re.escape(mark),lambda m:m[1]+comb,s)
    return unicodedata.normalize('NFC',s)

pages=[];notes={};warnings=[];last_sid=None;last_note=None;callmap={};image_pages=[1]
with pdfplumber.open(SOURCE) as pdf:
    for n,pg in enumerate(pdf.pages,1):
        ch=next((s for s in chapters if s['pdf_start']<=n<=s['pdf_end']),None)
        sec=ch or next(s for s in other if s['pdf_start']<=n<=s['pdf_end'])
        sid='ch'+str(ch['chapter']) if ch else sec['key'];prose=ch is not None
        if sid!=last_sid:last_sid=sid;last_note=None;callmap={}
        chars=[copy.copy(c) for c in pg.chars if c['top']<(580 if n>=20 else 610) and not(n>=20 and c['top']<55)]
        small=[c for c in chars if abs(c['size']-8.47)<.08] if prose else []
        note_top=min((c['top'] for c in small),default=10000)
        nc=[c for c in chars if c['top']>=note_top-1] if small else []
        bc=[c for c in chars if c['top']<note_top-1] if small else chars
        # Stacked fractions use the same size as note calls; recover them first.
        tiny=[c for c in bc if c['text'].isdigit() and abs(c['size']-7.32)<.08] if prose else []
        for numerator in tiny:
            denominator=next((z for z in tiny if abs(z['x0']-numerator['x0'])<1 and 7<z['top']-numerator['top']<9),None)
            if denominator is not None:
                key=numerator['text']+'/'+denominator['text']
                numerator['text']={'1/2':'½','1/4':'¼','3/4':'¾'}.get(key,key)
                numerator['top']+=3.5;denominator['text']=''
        supers=[c for c in bc if c['text'].isdigit() and (abs(c['size']-6.97)<.08 or abs(c['size']-7.32)<.08 or abs(c['size']-6.8)<.08 or abs(c['size']-7.97)<.08)] if prose else []
        groups=[]
        for c in sorted(supers,key=lambda c:(round(c['top']/2),c['x0'])):
            if groups and abs(groups[-1][-1]['top']-c['top'])<1 and -.3<=c['x0']-groups[-1][-1]['x1']<2:groups[-1].append(c)
            else:groups.append([c])
        refs=[]
        for g in groups:
            num=''.join(c['text'] for c in g);key=callmap.get(num,f'p{n:03}-{num}');callmap[num]=key;refs.append(key);g[0]['text']=f'[^{key}]'
            for c in g:c['top']+=3.2;c['bottom']+=3.2
            for c in g[1:]:c['text']=''
        def lines(cs):
            return pdfplumber.utils.chars_to_textmap(cs,x_tolerance=1,y_tolerance=3.5).extract_text_lines(return_chars=True) if cs else []
        ls=lines(bc);out=[];buf=[];kind='body';newdefs=[]
        base=min((l['x0'] for l in ls if 50<l['x0']<78),default=60)
        def flush():
            if buf:out.append(('> ' if kind=='quote' else '')+clean(' '.join(buf)));buf.clear()
        for l in ls:
            txt=clean(l['text'].strip())
            if not txt:continue
            fs=statistics.median(c['size'] for c in l['chars'] if c['text'].strip())
            if prose and fs>10.7:flush();out.append(('### ' if fs<13 else '## ')+txt);continue
            nk='quote' if prose and 9.1<fs<10 else 'body'
            if nk!=kind:flush();kind=nk
            elif prose and kind=='body' and base+7<l['x0']<base+16:flush()
            elif not prose:flush()
            buf.append(txt)
        flush()
        for l in lines(nc):
            txt=clean(l['text'].strip());m=re.match(r'^(\d{1,3})\.?\s+(.*)',txt)
            if m and m[1] in callmap and callmap[m[1]] not in notes:
                last_note=callmap[m[1]];notes[last_note]=m[2];newdefs.append(last_note)
            elif last_note:notes[last_note]+=' '+txt
            else:warnings.append(dict(page=n,unassigned_note=txt))
        text='\n\n'.join(out);refs=[k for k in refs if f'[^{k}]' in text]
        folio=None
        for l in pg.extract_text_lines(x_tolerance=1,y_tolerance=3):
            z=l['text'].strip()
            if 579<l['top']<616 and 175<l['x0']<250 and re.fullmatch(r'(?:\d\s*){1,3}|[ivxlcdm]+',z):folio=z.replace(' ','')
        orig=str(n-19) if 20<=n<=384 else str(n-1) if 386<=n<=718 else folio
        pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
        if pics and n not in image_pages:image_pages.append(n)
        pages.append(dict(pdf_page=n,original_page=orig,printed_folio=folio,
                          original_page_inferred=bool((20<=n<=384 or 386<=n<=718) and not folio),section_id=sid,
                          text=text,refs=refs,notes_started=newdefs,images=n in image_pages))
        pg.close()
        if n%100==0:print('Extracted',n,flush=True)
allrefs={k for p in pages for k in p['refs']}
issues=dict(unmatched_references=sorted(allrefs-set(notes)),unmatched_definitions=sorted(set(notes)-allrefs))
for s in chapters+other:
    ps=pages[s['pdf_start']-1:s['pdf_end']]
    s['source_notes']=sum(len(p['notes_started']) for p in ps)
    s['english_words_approx']=len(re.findall(r'\b[A-Za-z][A-Za-z’\'-]*\b',' '.join(p['text'] for p in ps)))
    s['conversion_issues']={k:[x for x in vs if s['pdf_start']<=int(x[1:4])<=s['pdf_end']] for k,vs in issues.items()}
d=dict(scope='第九卷；当前代理逐章翻译，沿用前八卷术语；源文件缺第20章原书366—384页',source_pdf=SOURCE.name,
       source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=720,
       source_publication_year=2006,editor='休·麦克劳德',
       translation_status='in_progress',proofreading_status='pending',pdf_status='pending',
       chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=sorted(image_pages),extraction_warnings=warnings)
d['chapters'][19].update(status='source_missing',missing_original_pages=[366,384],source_notes=0)
d['source_gaps']=[dict(chapter=20,title_zh=titles[19],original_start=366,original_end=384,placeholder_pdf_page=385,reason='源PDF缺章；书签明确标记Chapter 20 missing，原书页码365后直接跳至385。')]
for path,value in [(R/'翻译进度.json',d),(R/'卷九结构.json',bookmarks),(ROOT/'data/volume9/pages.json',pages),(ROOT/'data/volume9/notes.json',notes)]:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
print('Extracted',len(pages),'pages;',len(notes),'notes;',issues,'warnings',len(warnings),'image pages',image_pages,flush=True)
