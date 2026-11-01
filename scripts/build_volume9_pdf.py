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
        if (a in '-/' and b.isdigit()) or (b in '-/' and a.isdigit()):return False
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
R = ROOT / '第九卷'
TMP = ROOT / 'tmp/pdfs-volume9'
TMP.mkdir(parents=True, exist_ok=True)
DATA = json.loads((R/'翻译进度.json').read_text(encoding='utf-8-sig'))
OUT = Path(os.environ.get('CAMBRIDGE_PDF_OUTPUT_DIR', str(ROOT / 'output/pdf'))) / '09 世界基督教（1914-2000）（中文校订版，缺第20章）.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
assert DATA['translated_chapters']>=2 and not DATA.get('final_pdf_verified')
ITEMS = sorted([c for c in DATA['chapters']+DATA['other_sections'] if c['status']=='translated' or c['status']=='source_missing' and c.get('placeholder_only') and c.get('chapter') in DATA.get('authorized_skipped_chapters',[])], key=lambda x:x['pdf_start'])
EXPECTED_SOURCE_PAGES = [n for c in ITEMS for n in range(c['pdf_start'],c['pdf_end']+1)]
EXPECTED_NOTES = sum(c.get('translated_notes',0) for c in ITEMS)
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
 'h2':style('h2',fontName='Hei',fontSize=14,leading=21,spaceBefore=17,spaceAfter=10,alignment=TA_LEFT,keepWithNext=1),
 'h3':style('h3',fontName='Hei',fontSize=11.5,leading=18,spaceBefore=12,spaceAfter=7,alignment=TA_LEFT,keepWithNext=1),
 'h4':style('h4',fontName='Hei',fontSize=10.5,leading=16,spaceBefore=10,spaceAfter=5,alignment=TA_LEFT,keepWithNext=0),
 'table':style('table',fontSize=9,leading=14,spaceAfter=0,alignment=TA_LEFT),
 'bib':style('bib',fontSize=9,leading=12.7,spaceAfter=4,leftIndent=12,firstLineIndent=-12,alignment=TA_LEFT),
 'abbr':style('abbr',fontSize=9.1,leading=13.8,spaceAfter=3,alignment=TA_LEFT),
 'index':style('index',fontSize=9,leading=13.4,spaceAfter=4,alignment=TA_LEFT),
 'cover':style('cover',fontName='Hei',fontSize=31,leading=45,spaceAfter=20,alignment=TA_LEFT),
 'coverSmall':style('coverSmall',fontSize=12,leading=20,spaceAfter=12,alignment=TA_LEFT),
}

INDEX_PATH=ROOT/'data/volume9/index-entries.json'
INDEX_ROWS=json.loads(INDEX_PATH.read_text(encoding='utf-8')) if INDEX_PATH.exists() else []
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
    s=re.sub('[\u2010-\u2015\u1706\ufe58\ufe63\uff0d]', '-', s).replace('\u00ad','')
    runs=[];last=None;buf=[]
    for ch in s:
        f=font_for(ch,bold,italic,base)
        if f!=last and buf:
            runs.append(f'<font name="{last}">{html.escape("".join(buf))}</font>');buf=[]
        last=f;buf.append(ch)
    if buf:runs.append(f'<font name="{last}">{html.escape("".join(buf))}</font>')
    return ''.join(runs)

ref_counts=collections.Counter(); note_counts=collections.Counter(); image_names=[]
TOKEN=re.compile(r'(\[\^p\d+-(?:\d+|star)\]|\*\*[^\n]+?\*\*|\*[^\n*]+?\*|`[^`]+`|\[[^\]]+\]\((?:<[^>]+>|[^)]+)\))')

def note_num(n):return '*' if n.endswith('-star') else n.rsplit('-',1)[1]
def inline(s,sec,bold=False,italic=False,base='Song',is_index=False):
    s=re.sub(r'<a id="pdf-\d+"></a>|<!--.*?-->','',s,flags=re.S)
    out=[];pos=0
    for m in TOKEN.finditer(s):
        out.append(text_runs(s[pos:m.start()],bold,italic,base));t=m[0]
        if t.startswith('[^'):
            n=t[2:-1];key=f'{sec}-{n}';ref_counts[key]+=1
            out.append(f'<a name="ref-{key}"/><super><link href="#note-{key}" color="#405d72">{note_num(n)}</link></super>')
        elif t.startswith('**'):
            out.append(inline(t[2:-2],sec,True,italic,base))
        elif t.startswith('*'):
            out.append(inline(t[1:-1],sec,bold,True,base))
        elif t.startswith('`'):out.append(text_runs(t[1:-1],bold,italic,base))
        else:
            label=re.match(r'\[([^\]]+)\]',t)[1]
            target=t[t.index('](')+2:-1].strip('<>')
            fragment=inline(label,sec,bold,italic,base)
            if re.match(r'^(?:https?://|#pdf-\d+$)',target):
                fragment=f'<link href="{html.escape(target,quote=True)}" color="#405d72">{fragment}</link>'
            out.append(fragment)
        pos=m.end()
    out.append(text_runs(s[pos:],bold,italic,base))
    return ''.join(out)

def P(s,which='body',sec='book',**kw):
    s=s.replace('\n',' ')
    s=re.sub(r'<a id=\"pdf-\d+\"></a>|<!--.*?-->','',s)
    st=ST[which]
    if kw:st=ParagraphStyle(st.name+'-custom',parent=st,**kw)
    return Paragraph(inline(s,sec,base=st.fontName),st)

class Anchor(Flowable):
    def __init__(self,names):super().__init__();self.names=names;self.width=self.height=0
    def draw(self):
        for n in self.names:self.canv.bookmarkHorizontal(n,0,0)

class Title(Paragraph):
    def __init__(self,text,key,section,level=0,toc=False):
        st=ST['h1' if level==0 else 'h2' if level==1 else 'h3']
        fragment=None
        if level==0:
            def width(s):
                s=re.sub('[\u2010-\u2015]','-',s)
                return sum(pdfmetrics.stringWidth(ch,font_for(ch,bold=True),21) for ch in s)
            w=width(text)
            if w>WIDTH:
                # Slightly shrink headings that can fit on a single line. Longer
                # titles break at a semantic boundary, avoiding a one-word tail.
                if w*18/21<=WIDTH:
                    size=int((WIDTH-2)*21/w*10)/10
                    st=ParagraphStyle('h1-fit-'+section,parent=st,fontSize=size,leading=size*1.43)
                else:
                    # Prefer date and clause boundaries, otherwise balance at a
                    # Chinese character boundary without splitting Latin words.
                    candidates=[j for j in range(1,len(text))
                        if text[j] in '（：、' or text[j-1] in '：、']
                    if not candidates:
                        candidates=[j for j in range(1,len(text)) if ord(text[j-1])>=0x2e80 and ord(text[j])>=0x2e80]
                    if not candidates:candidates=[j for j in range(1,len(text)) if text[j].isspace()]
                    if not candidates:candidates=[len(text)//2]
                    j=min(candidates,key=lambda j:max(width(text[:j]),width(text[j:])))
                    parts=[text[:j].rstrip(),text[j:].lstrip()]
                    longest=max(width(s) for s in parts)
                    size=min(21,int((WIDTH-2)*21/longest*10)/10)
                    st=ParagraphStyle('h1-balanced-'+section,parent=st,fontSize=size,leading=size*1.43)
                    fragment='<br/>'.join(inline(s,section,bold=True) for s in parts)
        if fragment is None:fragment=inline(text,section,bold=True)
        super().__init__(fragment,st)
        self.key=key;self.plain=re.sub(r'\[\^p\d+-(?:\d+|star)\]','',text);self.plain=re.sub('[\u2010-\u2015]','-',self.plain);self.section=section;self.level=level;self.toc=toc

class Book(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=(W,H),leftMargin=M,rightMargin=M,topMargin=M+3*mm,bottomMargin=M+2*mm,
                         title='剑桥基督教史 第九卷：世界基督教（中文校订版，缺第20章）',
                         author='休·麦克劳德（编）',
                         subject=f'中文校订版：{DATA["translated_chapters"]}章及全部现有卷首卷末资料；{EXPECTED_NOTES}条原注；源PDF第20章缺失',
                         pageCompression=1,allowSplitting=1)
        self.section_title='剑桥基督教史 · 第九卷';self.section_pages={};self.pass_no=0
        normal=Frame(M,M+2*mm,WIDTH,HEIGHT,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        gutter=7*mm;cw=(WIDTH-gutter)/2
        ix=[Frame(M+i*(cw+gutter),M+2*mm,cw,HEIGHT,id=f'ix{i}',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0) for i in range(2)]
        self.addPageTemplates([PageTemplate('body',[normal],onPageEnd=self.furniture),
                              PageTemplate('index',ix,onPageEnd=self.furniture),
                              PageTemplate('cover',[normal],onPage=self.cover_page)])
    def beforeDocument(self):
        self.section_title='剑桥基督教史 · 第九卷';self.section_pages={};self.pass_no+=1;self.outline_level=0;self.headers=[]
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
    import shutil
    q=TMP/'figures';q.mkdir(exist_ok=True)
    for p in (R/'assets').iterdir():
        if p.suffix.lower() in {'.png','.jpg','.jpeg'}:shutil.copyfile(p,q/p.name)


def norm(s):return re.sub(r'[^a-z0-9]', '',unicodedata.normalize('NFKD',s).lower())
def bibliography_positions():
    # Chapter bibliographies are already recovered as one entry per paragraph.
    # The original line indentation is unnecessary for reliable hanging entries.
    return {}

SOURCE_PAGES=json.loads((ROOT/'data/volume9/pages.json').read_text(encoding='utf8'))
page_location={}
physical_anchors=[]
anchors_by_line=collections.defaultdict(list)
for c in ITEMS:
    for i,line in enumerate(c['text'].splitlines()):
        for match in re.finditer(r'<a id="pdf-(\d+)"></a>',line):
            physical=int(match[1]);physical_anchors.append(physical)
            anchors_by_line[(c['id'],i)].append(f'pdf-{physical:03}')
            if c.get('key')=='index':continue
            original=SOURCE_PAGES[physical-1]['original_page']
            if not original and 20<=physical<=384:original=physical-19
            elif not original and 386<=physical<=718:original=physical-1
            if original and str(original).isdigit():page_location[int(original)]=(1,c['id'],i)
assert physical_anchors==list(EXPECTED_SOURCE_PAGES)
for n,(_,sec,line) in page_location.items():anchors_by_line[(sec,line)].append(f'orig-{n}')


def index_inline(s,sec):
    # Protect inline Markdown emphasis first; indices contain no footnote calls.
    out=[];pos=0;prev_start=None
    for m in re.finditer(r'(\*{0,2})(\d+)(\*{0,2})',s):
        out.append(inline(s[pos:m.start()],sec));value=int(m[2])
        prefix=s[pos:m.start()]
        if re.search(r'[–—-]\s*$',prefix) and prev_start is not None:
            power=10**len(m[2]);candidate=prev_start//power*power+value
            if candidate<prev_start:candidate+=power
            value=candidate
        else:prev_start=value
        t=inline(m[2],sec,bold=m[1]==m[3]=='**',italic=m[1]==m[3]=='*')
        out.append(f'<link href="#orig-{value}" color="#405d72">{t}</link>' if value in page_location else t)
        pos=m.end()
    out.append(inline(s[pos:],sec))
    return ''.join(out)

def cross_index_inline(s,sec):
    # Cross-reference labels can contain both page locators and historical dates.
    # Only the locator group preceding the cross-reference sentence is linked.
    out=[];pos=0
    for m in re.finditer(r'，(\d[\d, –—-]*)(?=。|$)',s):
        out.append(inline(s[pos:m.start(1)],sec))
        out.append(index_inline(m[1],sec));pos=m.end(1)
    out.append(inline(s[pos:],sec));return ''.join(out)

def make_table(lines,sec,abbr=False):
    rows=[]
    for line in lines:
        cells=[x.strip() for x in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?',x) for x in cells):continue
        rows.append(cells)
    cols=max(map(len,rows));rows=[x+['']*(cols-len(x)) for x in rows]
    if cols==2:
        head=rows[0][0]
        if head in ['内容','章节','篇目与作者','卷首资料','图号与标题','图号与说明']:widths=[WIDTH*.86,WIDTH*.14]
        elif head=='缩略语':widths=[WIDTH*.19,WIDTH*.81]
        elif head in ['卷次与题名','卷名']:widths=[WIDTH*.60,WIDTH*.40]
        elif head=='撰稿人':widths=[WIDTH*.43,WIDTH*.57]
        elif head in ['原图标名','原图标记']:widths=[WIDTH*.49,WIDTH*.51]
        else:widths=[WIDTH*.5,WIDTH*.5]
    elif cols==3:
        widths=[WIDTH*.58,WIDTH*.30,WIDTH*.12] if rows[0][0] in ['章节','章次与题名','篇目'] else [WIDTH*.09,WIDTH*.79,WIDTH*.12] if rows[0][0]=='图号' else [WIDTH*.61,WIDTH*.27,WIDTH*.12] if rows[0][0]=='项目' else [WIDTH*.13,WIDTH*.48,WIDTH*.39] if rows[0][0]=='缩写' else [WIDTH*.14,WIDTH*.68,WIDTH*.18]
    elif cols==4 and rows[0][0]=='章':widths=[WIDTH*.075,WIDTH*.53,WIDTH*.265,WIDTH*.13]
    else:widths=[WIDTH/cols]*cols
    data=[[P(v,'table',sec,fontName='Hei' if j==0 else 'Song') for v in row] for j,row in enumerate(rows)]
    t=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT',splitByRow=1,splitInRow=1)
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
    sec=c['id'];lines=c['text'].splitlines();flow=[];i=0;heading_count=0;is_bib=c.get('key')=='bibliography';is_ix=c.get('key')=='index';ix_counter=0
    bib_page=0;bib_buffer=[];bib_indent=0;notes_seen=False;note_mode=False
    def flush_bib():
        nonlocal bib_buffer
        if bib_buffer:
            text=' '.join(bib_buffer)
            text=re.sub(r'-\s+', '-', text)
            flow.append(P(text,'bib',sec,leftIndent=12+(8 if bib_indent>=5 else 0)))
            bib_buffer=[]
    while i<len(lines):
        raw=lines[i];line=re.sub(r'<a id=\"pdf-\d+\"></a>|<!--.*?-->','',raw);st=line.strip()
        if (sec,i) in anchors_by_line:flow.append(Anchor(anchors_by_line[(sec,i)]))
        if not st or st=='（原书此页空白。）':i+=1;continue
        if st.startswith('<a '):i+=1;continue
        if st.startswith('<!--'):
            pm=re.search(r'PDF(?: page |第)(\d+)',st)
            if pm:bib_page=int(pm[1])
            i+=1;continue
        # These draft-source links and status sentences have no purpose in the book.
        if st=='《剑桥基督教史》第二卷《君士坦丁至约600年》中文译稿':i+=1;continue
        if re.match(r'^>\s*(?:\[|原书|对应原书|本节译自|未编号|本篇|正文)',st):
            if st.startswith('> ['):i+=1;continue
            meta=st.lstrip('> ').strip()
            if heading_count==1 and len(flow)<8 and not (is_bib or is_ix):
                # The compact source range replaces repetitive translator metadata.
                pass
            else:flow.append(P(meta,'meta',sec))
            i+=1;continue
        if st=='>':i+=1;continue
        if st.startswith('#'):
            flush_bib();m=re.match(r'^(#+)\s+(.+)',st);depth=len(m[1]);title=m[2]
            if c.get('key')=='front_matter' and title=='撰稿人':flow.append(PageBreak())
            if title=='参考文献':is_bib=True
            elif title in ['注释','脚注','章末注']:is_bib=False
            if depth==1:
                heading_count+=1
                flow.append(Title(title,sec,sec,toc=True))
                original_range=re.search(r'^>\s*(?:对应)?原书第\s*([\divxlc]+\s*(?:[–—-]\s*[\divxlc]+)?)\s*页',c['text'],re.M)
                if original_range:
                    flow.append(P('原书第'+original_range[1].replace(' ','')+'页','meta',sec))
                else:
                    orig=[p['original_page'] for p in SOURCE_PAGES[c['pdf_start']-1:c['pdf_end']] if p['original_page'] and str(p['original_page']).isdigit()]
                    meta=f"原书第{orig[0]}-{orig[-1]}页" if orig else f"原书 PDF 第{c['pdf_start']}-{c['pdf_end']}页"
                    flow.append(P(meta,'meta',sec))
            elif title.strip() in ['脚注','注释','章末注']:
                flow.extend([CondPageBreak(95),P('章末注','h2',sec)]);notes_seen=True
                flow.append(P('点击正文注号可跳转至注释；点击注释编号可返回正文。','meta',sec))
            else:
                heading_count+=1
                level=min(depth-1,2)
                heading=Title(title,f'{sec}-h{heading_count}',sec,level=level)
                if flow and isinstance(flow[-1],Title):flow.append(heading)
                else:flow.extend([CondPageBreak(heading.wrap(WIDTH,HEIGHT)[1]+75),heading])
            i+=1;continue
        if re.match(r'^\[\^p\d+-(?:\d+|star)\]:',st):
            flush_bib();m=re.match(r'^\[\^(p\d+-(?:\d+|star))\]:\s*(.*)$',st)
            if not m:raise ValueError((c['chinese_file'],i,st))
            n,text=m.groups();key=f'{sec}-{n}';note_counts[key]+=1
            if not notes_seen:
                flow.extend([CondPageBreak(95),P('章末注','h2',sec)]);notes_seen=True
            frag=f'<a name="note-{key}"/><link href="#ref-{key}" color="#405d72">{note_num(n)}.</link>　'+inline(text,sec)
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
        images=re.findall(r'!\[([^\]]*)\]\(([^)]+)\)',st)
        if images:
            flush_bib();figures=[];available=(WIDTH-8*(len(images)-1))/len(images)
            for alt,name in images:
                p=TMP/'figures'/Path(name).name
                if not p.exists():raise FileNotFoundError(p)
                iw,ih=PILImage.open(p).size;maxh=155*mm if p.name=='pdf-001.png' else 115*mm if p.name=='map-01.png' else HEIGHT*(.66 if len(images)>1 else .84)
                scale=min(available/iw,maxh/ih)
                fig=Image(str(p),width=iw*scale,height=ih*scale);fig.hAlign='CENTER';figures.append(fig);image_names.append(p.name)
            if len(figures)>1:
                fig=LongTable([figures],colWidths=[WIDTH/len(figures)]*len(figures),hAlign='CENTER')
                fig.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
            else:fig=figures[0]
            group=[Spacer(1,9),fig];j=i+1
            while j<len(lines) and not lines[j].strip():j+=1
            if j<len(lines) and lines[j].strip().startswith('*') and not lines[j].strip().startswith('**'):
                group.append(P(lines[j].strip().strip('*'),'caption',sec));i=j
            elif j<len(lines) and re.match(r'^\*{0,2}图\d+(?:\.\d+)?\s',lines[j].strip()):
                group.append(P(lines[j].strip(),'caption',sec));i=j
            else:group.append(P(images[0][0],'caption',sec))
            if flow and isinstance(flow[-1],Title):group.insert(0,flow.pop())
            flow.append(KeepTogether(group))
            i+=1;continue
        if st in ['---','***']:i+=1;continue
        if st.startswith('>'):
            flush_bib();buf=[]
            while i<len(lines) and lines[i].lstrip().startswith('>'):
                l=lines[i].lstrip()[1:].lstrip();buf.append(l.strip());i+=1
            # Short lines in creeds/poems retain explicit line divisions.
            if len(buf)>1 and sum(len(x) for x in buf)/len(buf)<110:
                frag='<br/>'.join(inline(x,sec,base='Song') for x in buf)
                flow.append(Paragraph(frag,ST['quote']))
            else:flow.append(P(' '.join(buf),'quote',sec))
            continue
        lm=re.match(r'^(\s*)(?:[-*]|\d+\.)\s+(.+)$',line)
        if lm:
            flush_bib();indent=len(lm[1]);txt=lm[2]
            if is_ix:
                stx=ParagraphStyle('ix-nest',parent=ST['index'],leftIndent=min(indent*2.5,22),firstLineIndent=0)
                r=INDEX_ROWS[ix_counter];ix_counter+=1
                stx.keepWithNext=int(ix_counter<len(INDEX_ROWS) and INDEX_ROWS[ix_counter]['level']>r['level'])
                refs=r['refs']
                if refs:
                    assert txt.endswith('，'+refs),(r,txt)
                    prefix=txt[:-len(refs)]
                    frag=inline(prefix,sec)+index_inline(refs,sec)
                elif re.search(r'\b[Ss]ee\b',r['label']):frag=cross_index_inline(txt,sec)
                else:frag=inline(txt,sec)
                flow.append(Paragraph(frag,stx))
            else:flow.append(P('• '+txt,'body',sec,leftIndent=10+indent*3,firstLineIndent=-8))
            i+=1;continue
        flush_bib();buf=[st];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^\s*(?:#|>|\[\^|!\[|\||```|<!--|<a |[-*]\s)',lines[i]):
            buf.append(lines[i].strip());i+=1
        txt=' '.join(buf)
        if txt.startswith('本部分扉页后的图版，已放在'):continue
        if re.fullmatch(r'\[(?:空白页|原书空白页)[^\]]*\]\(.+\)',txt):continue
        which='author' if (txt.startswith('**作者') or ('chapter' in c or c.get('key') in ['introduction','conclusion']) and len(flow)<5 and len(txt)<240) else 'bib' if is_bib else 'body'
        if txt.startswith('文献作者名、题名'):which='meta'
        if which=='bib':flow.append(P(txt,which,sec,leftIndent=21 if raw.startswith('    ') else 12))
        else:flow.append(P(txt,which,sec))
    flush_bib()
    return flow

def build():
    make_crops();bibpos=bibliography_positions()
    story=[NextPageTemplate('cover')]
    # Start the first page on the cover template as well as all subsequent covers.
    story += [Spacer(1,37*mm),P('剑桥基督教史','coverSmall'),
              P('第九卷','h2'),P('世界基督教','cover'),
              P('约1914—约2000年','coverSmall'),
              P('THE CAMBRIDGE HISTORY OF CHRISTIANITY','meta'),
              P('VOLUME IX · WORLD CHRISTIANITIES c.1914–c.2000','meta'),Spacer(1,14*mm),
              P('休·麦克劳德　主编','coverSmall'),
              Spacer(1,18*mm),P('中文校订版 · 原文缺第20章 · 2026年10月','meta'),
              NextPageTemplate('body'),PageBreak()]
    story += [Title('阅读说明','reading','reading'),
        P(f'本译稿依据剑桥大学出版社2006年英文原书，收入全部现有卷首资料、三编扉页、第1—19章与第21—33章，以及参考书目与索引。可用正文共32章，保留{EXPECTED_NOTES}条原书注释；覆盖源PDF的719页现有内容，并另设第385页原文缺失说明。'),
        P('译文已对照原文，完成一致性校订、重点复核，并检查页面衔接、原注对应及阅读版排版，尚未经独立专业逐句精校。文中“当前”“今天”、统计与任职信息均依原书写作时期，不表示2026年现状。'),
        P('原文缺口：原目录列有第20章《拉丁美洲基督教的转型（约1950-2000年）》，但源PDF缺少该章原书第366-384页，共19页。PDF第385页为占位空白页，书签明确注明缺章。按用户要求暂跳过该章，继续翻译其他32章及卷首卷末资料；缺章不计为已译。'),
        P('原书页下注集中排到各章末，保留原编号，正文注号与章末注编号之间可往返跳转。书目、注释及作者简介中的作者、原文题名、刊名与出版定位按学术惯例保留原文，说明性文字译为中文。已发现的原书疑点在相关段落及译校说明中标出，未据其他史料逐项核定。'),
        P('本阅读版目录及侧栏书签可跳转到各章。卷首目录、章末注及卷末索引中的文献定位保留英文原书页码；索引的有效原书页码可点击跳转。缺失的第366—384页保留数字，未设置跳转。缺章之前，正文原页码为源PDF页码减19；缺章之后为减1，与本阅读版页码不同。空白原页保留来源锚点，不另印为空白阅读页。'),
        PageBreak(),Title('目录','contents','contents')]
    toc=TableOfContents();toc.levelStyles=[style('toc',fontSize=9.3,leading=13,spaceBefore=0,spaceAfter=.5,leftIndent=0,rightIndent=23,alignment=TA_LEFT)]
    toc.dotsMinLevel=0;story.append(toc)
    for c in ITEMS:
        if c.get('key')=='index':story.append(NextPageTemplate('index'))
        else:story.append(NextPageTemplate('body'))
        story.append(PageBreak());story+=section_story(c,bibpos)
    assert len(ref_counts)==len(note_counts)==EXPECTED_NOTES,(len(ref_counts),len(note_counts))
    assert ref_counts==note_counts and all(n==1 for n in ref_counts.values())
    expected_images=[Path(name).name for c in ITEMS for name in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',c['text'])]
    assert sorted(image_names)==sorted(expected_images),image_names
    drawn={n for f in story if isinstance(f,Anchor) for n in f.names if n.startswith('pdf-')}
    assert drawn=={f'pdf-{n:03}' for n in EXPECTED_SOURCE_PAGES},('Missing source anchors',sorted({f'pdf-{n:03}' for n in EXPECTED_SOURCE_PAGES}-drawn))
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
              images=image_names,source_page_anchors=len(physical_anchors),original_numeric_page_anchors=len(page_location),passes=book.pass_no,
              missing_glyphs=dict(missing))
    (TMP/'build-manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PDF complete',OUT,'bytes',OUT.stat().st_size,flush=True)

if __name__=='__main__':build()
