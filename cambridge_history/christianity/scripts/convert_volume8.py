from pathlib import Path
from environment import poppler_tool, require_uninitialized
import collections, copy, hashlib, json, re, statistics, unicodedata
import pdfplumber
from pypdf import PdfReader
require_uninitialized(Path(__file__).resolve().parents[1] / '第八卷')

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'第八卷'; T=ROOT/'data/volume8'; A=R/'assets'
for p in (R,T,A): p.mkdir(exist_ok=True)
assert not (R/'翻译进度.json').exists() or all(x['status']=='pending' for x in (json.loads((R/'翻译进度.json').read_text(encoding='utf8'))['chapters']+json.loads((R/'翻译进度.json').read_text(encoding='utf8'))['other_sections'])), 'Initial extraction only; never reset translated work.'
SOURCE=ROOT/'08 世界基督教（1815-1914）.pdf'
reader=PdfReader(SOURCE)
bookmarks=json.loads((T/'outline.json').read_text(encoding='utf8'))
titles=[
'导论','教皇制度','神学与反抗启蒙运动','自愿性宗教的增长','礼拜与灵修中的天主教复兴',
'女性讲道人与新修会','教会建筑与宗教艺术','音乐潮流与西方教会：“古”与“今”的碰撞',
'基督教与英语文学','基督教社会思想','基督教与科学','历史与《圣经》','城乡民众宗教与不信宗教',
'法国的天主教：从王朝复辟到政教分离（1815—1905年）','意大利：教会与民族复兴运动',
'天主教、爱尔兰与爱尔兰离散群体','大匈牙利与波兰的天主教民族主义','基督教与德意志的建立',
'圣公会、长老宗与联合王国的宗教认同','新教的主导地位与宗派政治：瑞士和荷兰',
'斯堪的纳维亚：路德宗与民族认同','“基督教美国”与“基督教加拿大”','西班牙与葡萄牙：教会面临的挑战',
'拉丁美洲：教会与民族独立','东西方之间：东方天主教（“合一派”）教会','非裔美国人的基督教',
'基督教传教、反奴隶制与人道诉求（约1813—1873年）',
'中东：西方传教事业与东方教会、伊斯兰教、犹太教','英属印度帝国的基督徒与宗教传统',
'东亚的基督教：中国、朝鲜与日本','印度支那的基督教',
'作为教会与叙事的基督教，以及十九世纪菲律宾民族的诞生','澳大拉西亚与太平洋的基督教',
'传教与帝国（约1873—1914年）','埃塞俄比亚主义与现代非洲基督教的根源','1914年基督教的前景']
dividers=[28,232,444]
chapters=[]
for b in bookmarks:
    m=re.match(r'^(\d+)\.\s*(.*)',b['title'])
    if m:
        n=int(m[1]);chapters.append(dict(chapter=n,title=m[2],title_zh=titles[n-1],pdf_start=b['pdf_start']))
for i,c in enumerate(chapters):
    end=chapters[i+1]['pdf_start']-1 if i+1<len(chapters) else 617
    c['pdf_end']=min([end]+[n-1 for n in dividers if c['pdf_start']<n<=end])
    c.update(english_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（英文）.md',
             chinese_file=f'第{c["chapter"]:02}章 {c["title_zh"]}（中文）.md',status='pending')
other=[dict(key='front_matter',title_zh='卷首资料',pdf_start=1,pdf_end=17),
       *[dict(key=f'part{i+1}',title_zh='第'+['一','二','三'][i]+'编 '+title,pdf_start=n,pdf_end=n+1)
         for i,(n,title) in enumerate(zip(dividers,['基督教与现代性','教会与民族认同','基督教的扩展']))],
       dict(key='bibliography',title_zh='参考书目',pdf_start=618,pdf_end=672),
       dict(key='index',title_zh='索引',pdf_start=673,pdf_end=702)]
for s in other:
    s.update(english_file=s['title_zh']+'（英文）.md',chinese_file=s['title_zh']+'（中文）.md',status='pending')
assert sorted(n for s in chapters+other for n in range(s['pdf_start'],s['pdf_end']+1))==list(range(1,703))

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
        chars=[copy.copy(c) for c in pg.chars if c['top']<(580 if n>=18 else 610) and not(n>=18 and c['top']<55)]
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
        supers=[c for c in bc if c['text'].isdigit() and (abs(c['size']-7.32)<.08 or abs(c['size']-6.8)<.08 or abs(c['size']-7.97)<.08)] if prose else []
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
        orig=str(n-17) if 18<=n<=700 else folio
        pics=[im for im in pg.images if min(im.get('srcsize',(0,0)))>50]
        if pics and n not in image_pages:image_pages.append(n)
        pages.append(dict(pdf_page=n,original_page=orig,printed_folio=folio,
                          original_page_inferred=bool(18<=n<=700 and not folio),section_id=sid,
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
d=dict(scope='第八卷；当前代理逐章翻译，沿用前七卷术语',source_pdf=SOURCE.name,
       source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_pages=702,
       source_publication_year=2006,editor='谢里丹·吉利、布赖恩·斯坦利',
       translation_status='in_progress',proofreading_status='pending',pdf_status='pending',
       chapters=chapters,other_sections=other,conversion_issues=issues,image_pages=sorted(image_pages),extraction_warnings=warnings)
for path,value in [(R/'翻译进度.json',d),(R/'卷八结构.json',bookmarks),(ROOT/'data/volume8/pages.json',pages),(ROOT/'data/volume8/notes.json',notes)]:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
print('Extracted',len(pages),'pages;',len(notes),'notes;',issues,'warnings',len(warnings),'image pages',image_pages,flush=True)
