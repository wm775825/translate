from pathlib import Path
from environment import font_path
import os
import re, json, html, unicodedata, difflib, collections, sys
from PIL import Image as PILImage
import pdfplumber
import reportlab.platypus.paragraph as rl_paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, NextPageTemplate, Image, LongTable, TableStyle, Flowable,
    KeepTogether, CondPageBreak)
from reportlab.platypus.tableofcontents import TableOfContents

# Use ReportLab's native fragments and line renderer, with Chinese punctuation
# constraints and stable Western word breaks. The bundled splitter omits fullwidth
# commas/colons and fails on empty fragments used by named destinations.
def chinese_frag_split(frags,maxWidths,calcBounds,encoding='utf8'):
    U=[]
    for frag in frags:
        text=frag.text.decode(encoding) if isinstance(frag.text,bytes) else frag.text
        U.extend(rl_paragraph.cjkU(ch,frag,encoding) for ch in text or [''])
    cannot_start=set('，。；：！？、）》〉】」』〕］％‰…,.!?:;)]}’”')
    cannot_end=set('（《〈【「『〔［([{‘“')
    n=len(U);prev=['']*n;next_char=['']*n;p=''
    for j,u in enumerate(U):
        if u:p=str(u)
        prev[j]=p
    p=''
    for j in range(n-1,-1,-1):
        next_char[j]=p
        if U[j]:p=str(U[j])
    def allowed(j):
        if j>=n:return True
        a=prev[j-1] if j else '';b=next_char[j-1] if j else str(U[0])
        if not a or not b:return True
        if b in cannot_start or a in cannot_end or unicodedata.category(b).startswith('M'):return False
        # Keep an in-text superscript with the words it annotates.
        k=j
        while k<n and not U[k]:k+=1
        if k<n and getattr(U[k].frag,'rise',0)>0:return False
        return a.isspace() or b.isspace() or ord(a)>=0x2e80 or ord(b)>=0x2e80 or a in '-/'
    lines=[];start=0
    while start<n:
        width=maxWidths[min(len(lines),len(maxWidths)-1)];used=0;j=start;last=None;forced=False
        while j<n:
            u=U[j];w=u.width
            if hasattr(w,'normalizedValue'):w._normalizer=width;w=w.normalizedValue(width)
            if hasattr(u.frag,'lineBreak'):
                j+=1;forced=True;break
            if used+w>width+.0001 and j>start:break
            used+=w;j+=1
            if allowed(j):last=j
        if j<n and not forced and last and last>start:j=last
        if j<=start:j=start+1
        chunk=U[start:j]
        while chunk and str(chunk[-1]).isspace() and not hasattr(chunk[-1].frag,'cbDefn'):chunk.pop()
        used=sum(float(u.width) if not hasattr(u.width,'normalizedValue') else u.width.normalizedValue(width) for u in chunk)
        if chunk:lines.append(rl_paragraph.makeCJKParaLine(chunk,width,used,width-used,forced,calcBounds))
        start=j
        while start<n and str(U[start]).isspace() and not hasattr(U[start].frag,'cbDefn'):start+=1
    return rl_paragraph.ParaLines(kind=1,lines=lines)
rl_paragraph.cjkFragSplit=chinese_frag_split
_original_break_lines=Paragraph.breakLinesCJK
def all_chinese_lines(self,maxWidths):
    if not self.frags:return _original_break_lines(self,maxWidths)
    if not isinstance(maxWidths,(list,tuple)):maxWidths=[maxWidths]
    self.height=0
    rl_paragraph._handleBulletWidth(self.bulletText,self.style,maxWidths)
    if hasattr(self,'blPara') and getattr(self,'_splitpara',0):return self.blPara
    auto=getattr(self,'autoLeading',getattr(self.style,'autoLeading',''))
    return chinese_frag_split(self.frags,maxWidths,auto not in ('','off'))
Paragraph.breakLinesCJK=all_chinese_lines

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / '第一卷'
TMP = ROOT / 'tmp/pdfs'
OUT = Path(os.environ.get('CAMBRIDGE_PDF_OUTPUT_DIR', str(ROOT / 'output/pdf'))) / '01 起源至君士坦丁（中文校订版）.pdf'
TMP.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
DATA = json.loads((R/'翻译进度.json').read_text(encoding='utf-8-sig'))
ITEMS = sorted(DATA['chapters']+DATA['other_sections'], key=lambda x:x['pdf_start'])
for k,c in enumerate(ITEMS):
    c['id'] = f's{k:02}'
    c['text'] = (R/c['chinese_file']).read_text(encoding='utf-8-sig')

FONTFILES = {'Song':'simsun.ttc','Hei':'simhei.ttf','Kai':'simkai.ttf',
             'Latin':'times.ttf','LatinB':'timesbd.ttf','LatinI':'timesi.ttf',
             'LatinBI':'timesbi.ttf','Symbols':'seguisym.ttf','Arial':'arial.ttf'}
for name,file in FONTFILES.items():
    pdfmetrics.registerFont(TTFont(name,str(font_path(file))))
COVERAGE={n:set(pdfmetrics.getFont(n).face.charToGlyph) for n in FONTFILES}
INK=colors.HexColor('#263847'); MUTED=colors.HexColor('#64727b'); RULE=colors.HexColor('#d9dfe2')
W,H=176*mm,250*mm
M=19*mm
WIDTH=W-2*M
HEIGHT=H-2*M-5*mm

def style(name, **kw):
    base=dict(fontName='Song',fontSize=10.5,leading=17.5,textColor=INK,
              spaceAfter=6,wordWrap='CJK',allowWidows=0,allowOrphans=0,
              splitLongWords=1,alignment=TA_JUSTIFY)
    base.update(kw)
    return ParagraphStyle(name, **base)
ST={
 'body':style('body'),
 'quote':style('quote',fontName='Song',fontSize=10.2,leading=17,leftIndent=15,rightIndent=12,
               borderPadding=8,spaceBefore=4,spaceAfter=9,alignment=TA_LEFT),
 'note':style('note',fontSize=8.8,leading=13.1,leftIndent=17,firstLineIndent=-17,spaceAfter=5,alignment=TA_LEFT),
 'caption':style('caption',fontSize=8.6,leading=13.2,spaceBefore=4,spaceAfter=13,textColor=MUTED,alignment=TA_LEFT),
 'meta':style('meta',fontSize=8.5,leading=13,spaceAfter=12,textColor=MUTED,alignment=TA_LEFT),
 'author':style('author',fontSize=10,leading=16,spaceAfter=15,alignment=TA_LEFT),
 'h1':style('h1',fontName='Hei',fontSize=21,leading=30,spaceBefore=10,spaceAfter=14,alignment=TA_LEFT,keepWithNext=1),
 'h2':style('h2',fontName='Hei',fontSize=14,leading=21,spaceBefore=17,spaceAfter=10,alignment=TA_LEFT,keepWithNext=0),
 'h3':style('h3',fontName='Hei',fontSize=11.5,leading=18,spaceBefore=12,spaceAfter=7,alignment=TA_LEFT,keepWithNext=0),
 'h4':style('h4',fontName='Hei',fontSize=10.5,leading=16,spaceBefore=10,spaceAfter=5,alignment=TA_LEFT,keepWithNext=0),
 'table':style('table',fontSize=9,leading=14,spaceAfter=0,alignment=TA_LEFT),
 'bib':style('bib',fontSize=9,leading=12.7,spaceAfter=4,leftIndent=12,firstLineIndent=-12,alignment=TA_LEFT),
 'abbr':style('abbr',fontSize=9.1,leading=13.8,spaceAfter=3,alignment=TA_LEFT),
 'index':style('index',fontSize=9,leading=13.4,spaceAfter=4,alignment=TA_LEFT),
 'cover':style('cover',fontName='Hei',fontSize=31,leading=45,spaceAfter=20,alignment=TA_LEFT),
 'coverSmall':style('coverSmall',fontSize=12,leading=20,spaceAfter=12,alignment=TA_LEFT),
}

missing=collections.Counter()
def font_for(ch,bold=False,italic=False,base='Song'):
    if ord(ch)<0x2e80 and ch not in '。、「」『』【】（）《》〈〉，；：！？':
        f='LatinBI' if bold and italic else 'LatinB' if bold else 'LatinI' if italic else 'Latin'
    else:
        f='Hei' if bold else 'Kai' if italic else base
    if ord(ch) in COVERAGE.get(f,set()):return f
    for f in [base,'Song','Latin','Arial','Symbols']:
        if ord(ch) in COVERAGE[f]:return f
    missing[ch]+=1
    return 'Song'

def text_runs(s,bold=False,italic=False,base='Song'):
    s=unicodedata.normalize('NFC',s)
    s=re.sub('[\u2010-\u2015\u2212]', '-', s).replace('\u00ad','')
    runs=[];last=None;buf=[]
    for ch in s:
        f=font_for(ch,bold,italic,base)
        if f!=last and buf:
            runs.append(f'<font name="{last}">{html.escape("".join(buf))}</font>');buf=[]
        last=f;buf.append(ch)
    if buf:runs.append(f'<font name="{last}">{html.escape("".join(buf))}</font>')
    return ''.join(runs)

ref_counts=collections.Counter(); note_counts=collections.Counter(); image_names=[]
TOKEN=re.compile(r'(\[\^\d+\]|\*\*[^\n]+?\*\*|\*[^\n*]+?\*|`[^`]+`|\[[^\]]+\]\((?:<[^>]+>|[^)]+)\))')
def inline(s,sec,bold=False,italic=False,base='Song',is_index=False):
    out=[];pos=0
    for m in TOKEN.finditer(s):
        out.append(text_runs(s[pos:m.start()],bold,italic,base));t=m[0]
        if t.startswith('[^'):
            n=re.search(r'\d+',t)[0];key=f'{sec}-{n}';ref_counts[key]+=1
            out.append(f'<a name="ref-{key}"/><super><link href="#note-{key}" color="#405d72">{n}</link></super>')
        elif t.startswith('**'):
            out.append(inline(t[2:-2],sec,True,italic,base))
        elif t.startswith('*'):
            out.append(inline(t[1:-1],sec,bold,True,base))
        elif t.startswith('`'):out.append(text_runs(t[1:-1],bold,italic,base))
        else:
            label=re.match(r'\[([^\]]+)\]',t)[1]
            out.append(inline(label,sec,bold,italic,base))
        pos=m.end()
    out.append(text_runs(s[pos:],bold,italic,base))
    return ''.join(out)

def P(s,which='body',sec='book',**kw):
    st=ST[which]
    if kw:st=ParagraphStyle(st.name+'-custom',parent=st,**kw)
    return Paragraph(inline(s,sec,base=st.fontName),st)

class Anchor(Flowable):
    def __init__(self,names):super().__init__();self.names=names;self.width=self.height=0
    def draw(self):
        for n in self.names:self.canv.bookmarkHorizontal(n,0,0)

class Title(Paragraph):
    def __init__(self,text,key,section,level=0,toc=False):
        super().__init__(inline(text,section,bold=True), ST['h1' if level==0 else 'h2' if level==1 else 'h3'])
        self.key=key;self.plain=text;self.section=section;self.level=level;self.toc=toc

class Book(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=(W,H),leftMargin=M,rightMargin=M,topMargin=M+3*mm,bottomMargin=M+2*mm,
                         title='剑桥基督教史 第一卷：起源至君士坦丁（中文校订版）',
                         author='Margaret M. Mitchell, Frances M. Young（编）',
                         subject='全卷中文译稿；人名一致性校订与重点段落复核；含书目及索引',
                         pageCompression=1,allowSplitting=1)
        self.section_title='剑桥基督教史 · 第一卷';self.section_pages={};self.pass_no=0
        normal=Frame(M,M+2*mm,WIDTH,HEIGHT,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        gutter=7*mm;cw=(WIDTH-gutter)/2
        ix=[Frame(M+i*(cw+gutter),M+2*mm,cw,HEIGHT,id=f'ix{i}',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0) for i in range(2)]
        self.addPageTemplates([PageTemplate('body',[normal],onPageEnd=self.furniture),
                              PageTemplate('index',ix,onPageEnd=self.furniture),
                              PageTemplate('cover',[normal],onPage=self.cover_page)])
    def beforeDocument(self):
        self.section_title='剑桥基督教史 · 第一卷';self.section_pages={};self.pass_no+=1;self.outline_level=0;self.headers=[]
        print('Layout pass',self.pass_no,flush=True)
    def cover_page(self,c,doc):pass
    def furniture(self,c,doc):
        c.saveState();c.setStrokeColor(RULE);c.setLineWidth(.35)
        c.line(M,H-M+3*mm,W-M,H-M+3*mm)
        title=self.section_title
        c.setFont('Song',7.7);c.setFillColor(MUTED)
        while pdfmetrics.stringWidth(title,'Song',7.7)>WIDTH:title=title[:-2]+'…'
        c.drawString(M,H-M+7*mm,title)
        self.headers.append(title)
        c.setFont('Latin',9);c.drawCentredString(W/2,M-7*mm,str(doc.page))
        c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Title):
            self.canv.bookmarkHorizontalAbsolute(f.key,self.frame._y+f.height)
            level=min(f.level,self.outline_level+1)
            self.canv.addOutlineEntry(f.plain,f.key,level=level,closed=level>0)
            self.outline_level=level
            if f.level==0:
                self.section_title=f.plain
                self.section_pages[f.section]=dict(title=f.plain,page=self.page)
            if f.toc:self.notify('TOCEntry',(0,inline(f.plain,f.section),self.page,f.key))

# Use the original PDF's image placement to crop facsimiles without including
# English body text or running headers in a figure.
def make_crops():
    record={}
    with pdfplumber.open(ROOT/'01 起源至君士坦丁.pdf') as pdf:
        for p in sorted((R/'assets').glob('*.png')):
            n=int(p.stem.split('-')[1]);im=PILImage.open(p).convert('RGB');pg=pdf.pages[n-1]
            candidates=[x for x in pg.images if x.get('srcsize',(0,0))[0]>10 and x.get('srcsize',(0,0))[1]>10]
            if n in [1,4,23,24]:box=(0,0,im.width,im.height)
            elif n in [25,47]:continue
            elif n==48:box=(0,0,im.width,int(im.height*.95))
            elif n==85:box=(int(im.width*.17),int(im.height*.11),int(im.width*.885),int(im.height*.889))
            elif candidates:
                x=max(candidates,key=lambda a:(a['x1']-a['x0'])*(a['bottom']-a['top']))
                box=(max(0,int(x['x0']/pg.width*im.width)-2),max(0,int(x['top']/pg.height*im.height)-2),
                     min(im.width,round(x['x1']/pg.width*im.width)+2),min(im.height,round(x['bottom']/pg.height*im.height)+2))
            else:raise ValueError(('No crop',n))
            q=TMP/'figures'/p.name;q.parent.mkdir(exist_ok=True);im.crop(box).save(q)
            record[p.name]=dict(box=box,original_size=im.size)
    (TMP/'figure-crops.json').write_text(json.dumps(record,indent=2),encoding='utf-8')

def norm(s):return re.sub(r'[^a-z0-9]', '',unicodedata.normalize('NFKD',s).lower())
def bibliography_positions():
    cache=TMP/'bibliography-lines.json'
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    result={}
    with pdfplumber.open(ROOT/'01 起源至君士坦丁.pdf') as pdf:
        for n in range(639,732):
            pg=pdf.pages[n-1]
            lines=[l for l in pg.extract_text_lines() if l['top']>50 and l['bottom']<pg.height-30 and l['x0']<100]
            if not lines:continue
            margin=min(l['x0'] for l in lines)
            result[str(n)]=[(norm(l['text']),round(l['x0']-margin,2)) for l in lines]
    cache.write_text(json.dumps(result),encoding='utf-8');return result

def source_pages(s):
    m=re.search(r'原书第\s*(\d+)\s*(?:[–—-]\s*(\d+))?\s*页',s)
    if not m:return []
    a=int(m[1]);b=int(m[2] or a)
    return list(range(a,b+1)) if 1<=a<=b<=589 else []

# Source-page anchors use the narrowest page marker available. If the translation
# groups several pages into a block, their locators lead to that block's start.
page_location={}
for c in ITEMS:
    if c['pdf_start']>=639:continue
    ls=c['text'].splitlines()
    for i,line in enumerate(ls):
        if line.strip().startswith('<!--'):
            pages=source_pages(line)
            for n in pages:
                candidate=(len(pages),c['id'],i)
                if n not in page_location or candidate<page_location[n]:page_location[n]=candidate
for n in range(1,590):
    if n not in page_location:
        suitable=[c for c in ITEMS if c['pdf_start']<=n+49<=c['pdf_end']]
        c=suitable[-1] if suitable else min(ITEMS,key=lambda c:abs(c['pdf_start']-n-49))
        page_location[n]=(999,c['id'],0)
anchors_by_line=collections.defaultdict(list)
for n,(_,sec,line) in page_location.items():anchors_by_line[(sec,line)].append(f'orig-{n}')

def index_inline(s,sec):
    # Protect inline Markdown emphasis first; indices contain no footnote calls.
    out=[];pos=0;prev_start=None
    for m in re.finditer(r'\d+',s):
        out.append(inline(s[pos:m.start()],sec));value=int(m[0])
        prefix=s[pos:m.start()]
        if re.search(r'[–—-]\s*$',prefix) and prev_start is not None:
            power=10**len(m[0]);candidate=prev_start//power*power+value
            if candidate<prev_start:candidate+=power
            value=candidate
        else:prev_start=value
        t=inline(m[0],sec)
        out.append(f'<link href="#orig-{value}" color="#405d72">{t}</link>' if value in page_location else t)
        pos=m.end()
    out.append(inline(s[pos:],sec))
    return ''.join(out)

def make_table(lines,sec,abbr=False):
    rows=[]
    for line in lines:
        cells=[x.strip() for x in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?',x) for x in cells):continue
        rows.append(cells)
    cols=max(map(len,rows));rows=[x+['']*(cols-len(x)) for x in rows]
    if cols==2:widths=[WIDTH*.31,WIDTH*.69]
    elif cols==3:widths=[WIDTH*.21,WIDTH*.35,WIDTH*.44]
    else:widths=[WIDTH/cols]*cols
    data=[[P(v,'table',sec,fontName='Hei' if j==0 else 'Song') for v in row] for j,row in enumerate(rows)]
    t=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
        ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f3')),('LINEBELOW',(0,0),(-1,0),.65,MUTED),
        ('LINEBELOW',(0,1),(-1,-1),.25,RULE)]))
    return [t,Spacer(1,9)]

def abbreviation_block(lines,sec):
    flow=[];buffer=[]
    def flush():
        if buffer:
            a,b=buffer.pop()
            flow.append(P(('**'+a+'**　' if a else '')+b,'abbr',sec))
    for line in lines:
        if not line.strip():flush();flow.append(Spacer(1,3));continue
        if line.startswith('    ') and re.search('[\u4e00-\u9fff]',line):
            flush();flow.extend([CondPageBreak(64),P(line.strip(),'h3',sec)]);continue
        m=re.match(r'^\s*(\S.*?)\s{2,}(\S.*)$',line)
        if m:
            flush();buffer.append((m[1],m[2]))
        elif line.startswith(' '):
            if buffer:
                a,b=buffer.pop();buffer.append((a,b+' '+line.strip()))
            else:buffer.append(('',line.strip()))
        else:flush();buffer.append(('',line.strip()))
    flush();return flow

def section_story(c,bibpos):
    sec=c['id'];lines=c['text'].splitlines();flow=[];i=0;heading_count=0;is_bib=c.get('key')=='bibliography';is_ix=c.get('key')=='index'
    bib_page=639;bib_buffer=[];bib_indent=0;notes_seen=False;note_mode=False
    def flush_bib():
        nonlocal bib_buffer
        if bib_buffer:
            text=' '.join(bib_buffer)
            text=re.sub(r'-\s+', '-', text)
            flow.append(P(text,'bib',sec,leftIndent=12+(8 if bib_indent>=5 else 0)))
            bib_buffer=[]
    while i<len(lines):
        line=lines[i];st=line.strip()
        if (sec,i) in anchors_by_line:flow.append(Anchor(anchors_by_line[(sec,i)]))
        if not st:i+=1;continue
        if st.startswith('<a '):i+=1;continue
        if st.startswith('<!--'):
            pm=re.search(r'PDF(?: page |第)(\d+)',st)
            if pm:bib_page=int(pm[1])
            i+=1;continue
        # These draft-source links and status sentences have no purpose in the book.
        if st=='《剑桥基督教史》第一卷《起源至君士坦丁》中文译稿':i+=1;continue
        if re.match(r'^>\s*(?:\[|原书|对应原书|本节译自|未编号|本篇|正文)',st):
            if st.startswith('> ['):i+=1;continue
            meta=st.lstrip('> ').strip()
            if heading_count==1 and len(flow)<8:
                # The compact source range replaces repetitive translator metadata.
                pass
            else:flow.append(P(meta,'meta',sec))
            i+=1;continue
        if st=='>':i+=1;continue
        if st.startswith('#'):
            flush_bib();m=re.match(r'^(#+)\s+(.+)',st);depth=len(m[1]);title=m[2]
            if depth==1:
                heading_count+=1
                flow.append(Title(title,sec,sec,toc=True))
                original_range=re.search(r'^>\s*(?:对应)?原书第\s*([\divxlc]+\s*(?:[–—-]\s*[\divxlc]+)?)\s*页',c['text'],re.M)
                if original_range:
                    flow.append(P('原书第'+original_range[1].replace(' ','')+'页','meta',sec))
                elif c['pdf_start']>=50:
                    a=max(1,c['pdf_start']-49);b=min(740,c['pdf_end']-49)
                    if b>=a:flow.append(P(f'原书第{a}-{b}页','meta',sec))
                else:flow.append(P(f'原书 PDF 第{c["pdf_start"]}-{c["pdf_end"]}页','meta',sec))
            elif title.strip() in ['脚注','注释','章末注']:
                flow.extend([CondPageBreak(95),P('章末注','h2',sec)]);notes_seen=True
                flow.append(P('点击正文注号可跳转至注释；点击注释编号可返回正文。','meta',sec))
            elif is_bib and title=='参考文献':pass
            else:
                heading_count+=1
                level=min(depth-1,2)
                heading=Title(title,f'{sec}-h{heading_count}',sec,level=level)
                flow.extend([CondPageBreak(heading.wrap(WIDTH,HEIGHT)[1]+75),heading])
            i+=1;continue
        if st.startswith('[^'):
            flush_bib();m=re.match(r'^\[\^(\d+)\]:\s*(.*)$',st)
            if not m:raise ValueError((c['chinese_file'],i,st))
            n,text=m.groups();key=f'{sec}-{n}';note_counts[key]+=1
            if not notes_seen:
                flow.extend([CondPageBreak(95),P('章末注','h2',sec)]);notes_seen=True
            frag=f'<a name="note-{key}"/><link href="#ref-{key}" color="#405d72">{n}.</link>　'+inline(text,sec)
            flow.append(Paragraph(frag,ST['note']));i+=1;continue
        if st.startswith('```'):
            flush_bib();buf=[];i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i]);i+=1
            flow+=abbreviation_block(buf,sec);i+=1;continue
        if st.startswith('|'):
            flush_bib();buf=[]
            while i<len(lines) and lines[i].strip().startswith('|'):buf.append(lines[i]);i+=1
            flow+=make_table(buf,sec);continue
        im=re.match(r'!\[([^\]]*)\]\(([^)]+)\)',st)
        if im:
            flush_bib();p=TMP/'figures'/Path(im[2]).name
            if p.exists():
                iw,ih=PILImage.open(p).size
                maxh=HEIGHT*.72
                if p.stem in ['pdf-001','pdf-004']:maxh=HEIGHT*.62
                scale=min(WIDTH/iw,maxh/ih)
                fig=Image(str(p),width=iw*scale,height=ih*scale);fig.hAlign='CENTER'
                group=[Spacer(1,9),fig]
                # Keep the Chinese caption beside its image across page breaks.
                j=i+1
                while j<len(lines) and not lines[j].strip():j+=1
                if j<len(lines) and lines[j].strip().startswith('*') and not lines[j].strip().startswith('**'):
                    cap=lines[j].strip().strip('*');group.append(P(cap,'caption',sec));i=j
                else:group.append(P(im[1],'caption',sec))
                flow.append(KeepTogether(group));image_names.append(p.name)
            i+=1;continue
        if st in ['---','***']:i+=1;continue
        if st.startswith('>'):
            flush_bib();buf=[]
            while i<len(lines) and lines[i].lstrip().startswith('>'):
                l=lines[i].lstrip()[1:].lstrip();buf.append(l.strip());i+=1
            # Short lines in creeds/poems retain explicit line divisions.
            if len(buf)>2 and sum(len(x) for x in buf)/len(buf)<110:
                frag='<br/>'.join(inline(x,sec,base='Song') for x in buf)
                flow.append(Paragraph(frag,ST['quote']))
            else:flow.append(P(' '.join(buf),'quote',sec))
            continue
        lm=re.match(r'^(\s*)(?:[-*]|\d+\.)\s+(.+)$',line)
        if lm:
            flush_bib();indent=len(lm[1]);txt=lm[2]
            if is_ix:
                stx=ParagraphStyle('ix-nest',parent=ST['index'],leftIndent=min(indent*2.5,22),firstLineIndent=0)
                flow.append(Paragraph(index_inline(txt,sec),stx))
            else:flow.append(P('• '+txt,'body',sec,leftIndent=10+indent*3,firstLineIndent=-8))
            i+=1;continue
        if is_bib and len(re.findall('[\u4e00-\u9fff]',st))<30 and not st.startswith('**'):
            candidates=bibpos.get(str(bib_page),[]);key=norm(st)
            exact=[x for x in candidates if x[0]==key]
            if exact:indent=exact[0][1]
            else:
                ranked=sorted(((difflib.SequenceMatcher(None,key,k,autojunk=False).ratio(),ind) for k,ind in candidates),reverse=True)
                indent=ranked[0][1] if ranked and ranked[0][0]>.83 else (18 if bib_buffer and not re.search(r'[.!?。]\s*$',bib_buffer[-1]) else 0)
            if indent<13:flush_bib();bib_indent=indent
            bib_buffer.append(st.rstrip());i+=1;continue
        flush_bib();buf=[st];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^\s*(?:#|>|\[\^|!\[|\||```|<!--|<a |[-*]\s)',lines[i]):
            buf.append(lines[i].strip());i+=1
        txt=' '.join(buf)
        if txt.startswith('本部分扉页后的图版，已放在'):continue
        if re.fullmatch(r'\[(?:空白页|原书空白页)[^\]]*\]\(.+\)',txt):continue
        which='author' if txt.startswith('**作者') else 'body'
        flow.append(P(txt,which,sec))
    flush_bib()
    return flow

def build():
    make_crops();bibpos=bibliography_positions()
    story=[NextPageTemplate('cover')]
    # Start the first page on the cover template as well as all subsequent covers.
    story += [Spacer(1,37*mm),P('剑桥基督教史','coverSmall'),
              P('第一卷','h2'),P('起源至君士坦丁','cover'),
              P('THE CAMBRIDGE HISTORY OF CHRISTIANITY','meta'),
              P('VOLUME I · ORIGINS TO CONSTANTINE','meta'),Spacer(1,20*mm),
              P('玛格丽特·M.米切尔　弗朗西丝·M.杨　主编','coverSmall'),
              Spacer(1,24*mm),P('中文校订版 · 2026年10月','meta'),
              NextPageTemplate('body'),PageBreak()]
    story += [Title('阅读说明','reading','reading'),
        P('本译稿依据2006年英文原书，经Markdown中转翻译与排版。全卷包含32个编号章节、序篇、结语及卷首卷末资料。'),
        P('本次校订统一了人名译法，并对重点引文、疑似误译及尼西亚会议一章的复杂句逐段对照英文复核。校订范围不等同于全卷逐句独立复审。原书本身的疑点、年代差异和作者观点，依原文保留，并见各章译校说明。'),
        P('目录与侧栏书签可直接跳转。正文中的注号连接到本章章末注，点击注释编号可返回正文。参考文献的作者名、题名、刊名和定位保留原文，便于查找。'),
        P('索引中的页码是英文原书的印刷页码，与本PDF的页码不同。蓝色页码可跳转到译稿对应的原书页段；若译稿将几页合为一个段落组，则定位到该组开头。'),
        P('原文的斜体强调在中文中以楷体区分，外文仍使用斜体；尼西亚信经中特别标记的词句依此保留。'),
        P('插图、地图及原表图像保留原图，附中文图注或说明。图内文字沿用原文。'),
        PageBreak(),Title('目录','contents','contents')]
    toc=TableOfContents();toc.levelStyles=[style('toc',fontSize=10,leading=15.6,spaceBefore=3.5,spaceAfter=3,leftIndent=0,rightIndent=23,alignment=TA_LEFT)]
    toc.dotsMinLevel=0;story.append(toc)
    for c in ITEMS:
        if c.get('key')=='index':story.append(NextPageTemplate('index'))
        story.append(PageBreak());story+=section_story(c,bibpos)
    assert len(ref_counts)==len(note_counts)==2212,(len(ref_counts),len(note_counts))
    assert ref_counts==note_counts and all(n==1 for n in ref_counts.values())
    if missing:raise ValueError(('Missing glyphs',dict(missing)))
    book=Book(OUT)
    book._firstPageTemplateIndex=2
    print('Flowables',len(story),'notes',len(note_counts),'images',len(image_names),flush=True)
    book.multiBuild(story,maxPasses=5)
    def plain(flows):
        result=[]
        for f in flows:
            if isinstance(f,Paragraph):result.append(f.getPlainText())
            elif isinstance(f,LongTable):
                for row in f._cellvalues:
                    for cell in row:
                        result+=plain(cell if isinstance(cell,(list,tuple)) else [cell])
            elif isinstance(f,KeepTogether):result+=plain(f._content)
        return result
    expected=plain(story)+[re.sub(r'<[^>]+>','',entry[1]) for entry in toc._lastEntries]+book.headers
    (TMP/'expected-text.json').write_text(json.dumps(expected,ensure_ascii=False),encoding='utf-8')
    info=dict(output=str(OUT),sections=book.section_pages,footnotes=len(note_counts),
              images=image_names,source_page_anchors=len(page_location),passes=book.pass_no,
              missing_glyphs=dict(missing))
    (TMP/'build-manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PDF complete',OUT,'bytes',OUT.stat().st_size,flush=True)

if __name__=='__main__':build()
