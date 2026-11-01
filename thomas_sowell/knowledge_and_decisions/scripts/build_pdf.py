"""Build the complete reading PDF from the assembled, current Chinese Markdown."""
import collections,hashlib,html,json,re,unicodedata,os
from pathlib import Path
from PIL import Image as PILImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfdoc
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT,TA_CENTER,TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,PageBreak,Image,Flowable,KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents
import pdf_typography

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/pdfs/知识与决策（中文校订版）.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
INPUT=ROOT/'知识与决策（中文校订版）.md'
FONTFILES={'Song':'simsun.ttc','Hei':'simhei.ttf','Kai':'simkai.ttf','Latin':'times.ttf','LatinB':'timesbd.ttf','LatinI':'timesi.ttf','LatinBI':'timesbi.ttf','Symbols':'seguisym.ttf','Arial':'arial.ttf'}
FONTDIR=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
for name,file in FONTFILES.items():pdfmetrics.registerFont(TTFont(name,str(FONTDIR/file)))
COVERAGE={n:set(pdfmetrics.getFont(n).face.charToGlyph) for n in FONTFILES}
W,H=176*mm,250*mm;M=19*mm;WIDTH=W-2*M;BOTTOM=M+2*mm;TOP=H-M-3*mm
INK=colors.HexColor('#263847');MUTED=colors.HexColor('#64727b');RULE=colors.HexColor('#d9dfe2');LINK='#405d72'
missing=collections.Counter();refs=collections.Counter();anchors=collections.Counter();defs=collections.Counter()
units=[];images=[]
def font_for(ch,bold=False,italic=False,base='Song'):
    if ord(ch)<0x2e80 and ch not in '，。；：！？、（）《》【】“”‘’—…':
        f='LatinBI' if bold and italic else 'LatinB' if bold else 'LatinI' if italic else 'Latin'
    else:f='Hei' if bold else 'Kai' if italic else base
    if ord(ch) in COVERAGE[f]:return f
    for f in [base,'Song','Latin','Arial','Symbols']:
        if ord(ch) in COVERAGE[f]:return f
    missing[ch]+=1;return 'Song'
def runs(s,bold=False,italic=False,base='Song'):
    result=[];last=None;buf=[]
    for ch in unicodedata.normalize('NFC',s.replace('\n',' ').replace('\r',' ').replace('\t',' ')):
        f=font_for(ch,bold,italic,base)
        if f!=last and buf:result.append(f'<font name="{last}">{html.escape("".join(buf))}</font>');buf=[]
        last=f;buf.append(ch)
    if buf:result.append(f'<font name="{last}">{html.escape("".join(buf))}</font>')
    return ''.join(result)
TOKEN=re.compile(r'(<a id="[^"]+"></a>|<!--.*?-->|\[\^[^\]]+\]|\*\*[^\n]+?\*\*|\*[^\n*]+?\*|`[^`]+`|\[[^\]]+\]\((?:<[^>]+>|[^)]+)\))',re.S)
def inline(s,bold=False,italic=False,base='Song'):
    result=[];pos=0
    for m in TOKEN.finditer(s):
        result.append(runs(s[pos:m.start()],bold,italic,base));t=m[0]
        if t.startswith('<!--'):pass
        elif t.startswith('<a id='):
            key=re.search(r'id="([^"]+)"',t)[1];anchors[key]+=1;result.append(f'<a name="{key}"/>')
        elif t.startswith('[^'):
            nid=t[2:-1];refs[nid]+=1;key=f'ref-{nid}-{refs[nid]}'
            result.append(f'<a name="{key}"/><super><link href="#note-{nid}" color="{LINK}">{runs(nid.rsplit("-",1)[1])}</link></super>')
        elif t.startswith('**'):result.append(inline(t[2:-2],True,italic,base))
        elif t.startswith('*'):result.append(inline(t[1:-1],bold,True,base))
        elif t.startswith('`'):result.append(runs(t[1:-1],bold,italic,base))
        else:
            label=re.match(r'\[([^\]]+)\]',t)[1];target=t[t.index('](')+2:-1].strip('<>')
            frag=inline(label,bold,italic,base)
            if target.startswith(('https://','http://','#')):frag=f'<link href="{html.escape(target,quote=True)}" color="{LINK}">{frag}</link>'
            result.append(frag)
        pos=m.end()
    result.append(runs(s[pos:],bold,italic,base));return ''.join(result)
def style(name,**kw):
    args=dict(fontName='Song',fontSize=10.5,leading=17.5,textColor=INK,spaceAfter=6,wordWrap='CJK',allowWidows=0,allowOrphans=0,splitLongWords=1,alignment=TA_JUSTIFY)
    args.update(kw);return ParagraphStyle(name,**args)
ST={'body':style('body'),'quote':style('quote',fontSize=10.2,leading=17,leftIndent=15,rightIndent=12,spaceBefore=3,spaceAfter=9,alignment=TA_LEFT),
    'original_toc':style('original_toc',fontSize=9.5,leading=14.5,spaceAfter=1,alignment=TA_LEFT),
    'editorial':style('editorial',fontSize=9,leading=14,textColor=MUTED,leftIndent=12,rightIndent=8,spaceBefore=4,spaceAfter=8,alignment=TA_LEFT),
    'note':style('note',fontSize=8.8,leading=13.3,leftIndent=19,firstLineIndent=-19,spaceAfter=6,alignment=TA_LEFT),
    'index':style('index',fontSize=9.3,leading=14.8,spaceAfter=3,alignment=TA_LEFT),
    'meta':style('meta',fontSize=8.5,leading=13,textColor=MUTED,alignment=TA_LEFT),
    'h1':style('h1',fontName='Hei',fontSize=21,leading=30,spaceBefore=10,spaceAfter=17,alignment=TA_LEFT,keepWithNext=True),
    'h2':style('h2',fontName='Hei',fontSize=14,leading=21,spaceBefore=16,spaceAfter=9,alignment=TA_LEFT,keepWithNext=True),
    'h3':style('h3',fontName='Hei',fontSize=11.5,leading=18,spaceBefore=12,spaceAfter=7,alignment=TA_LEFT,keepWithNext=True),
    'cover':style('cover',fontName='Hei',fontSize=32,leading=46,spaceAfter=20,alignment=TA_LEFT),
    'coverSmall':style('coverSmall',fontSize=12,leading=21,spaceAfter=15,alignment=TA_LEFT)}
def plain(s):
    s=re.sub(r'<!--.*?-->|<a id="[^"]+"></a>','',s,flags=re.S)
    s=re.sub(r'\[\^([^\]]+)\]',lambda m:m[1].rsplit('-',1)[1],s)
    s=re.sub(r'\[([^\]]+)\]\((?:<[^>]+>|[^)]+)\)',r'\1',s)
    s=re.sub(r'\*\*([^\n]+?)\*\*',r'\1',s)
    s=re.sub(r'\*([^\n*]+?)\*',r'\1',s)
    return re.sub(r'`([^`]+)`',r'\1',s)
def P(text,which='body',bold=False,**kwargs):
    st=ST[which];units.append(plain(text))
    if kwargs:st=ParagraphStyle(st.name+'-custom',parent=st,**kwargs)
    return Paragraph(inline(text,bold=bold,base=st.fontName),st)
class Anchor(Flowable):
    def __init__(self,names):super().__init__();self.names=names;self.width=self.height=0
    def draw(self):
        for name in self.names:self.canv.bookmarkHorizontal(name,0,0)
class Title(Paragraph):
    def __init__(self,text,key,level=0,toc=True):
        self.key=key;self.level=level;self.plain=plain(text);self.toc=toc
        units.append(self.plain)
        st=ST['h1' if level==0 else 'h2' if level==1 else 'h3']
        if self.plain.startswith(('第一部分','第二部分')):st=ParagraphStyle('part-title',parent=st,keepWithNext=False)
        super().__init__(inline(text,bold=True,base='Hei'),st)
class NamedCanvas(Canvas):
    def save(self):
        pairs=[]
        for name,dest in sorted(self._destinations.items()):pairs.extend([pdfdoc.PDFString(name),dest])
        self._doc.Catalog.Names=pdfdoc.PDFDictionary({'Dests':pdfdoc.PDFDictionary({'Names':pdfdoc.PDFArray(pairs)})})
        super().save()
class Book(BaseDocTemplate):
    def __init__(self):
        super().__init__(str(OUT),pagesize=(W,H),leftMargin=M,rightMargin=M,topMargin=M+3*mm,bottomMargin=BOTTOM,title='知识与决策（中文校订版）',author='托马斯·索维尔',subject='十章正文、1996年版序言及全部1001条原注',pageCompression=1)
        frame=Frame(M,BOTTOM,WIDTH,TOP-BOTTOM,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate('body',[frame],onPageEnd=self.furniture));self.pass_no=0
    def beforeDocument(self):
        self.current='知识与决策';self.sections={};self.headings=[];self.outline_level=0;self.pass_no+=1
        print('Layout pass',self.pass_no,flush=True)
    def furniture(self,c,doc):
        if doc.page==1:return
        c.saveState();c.setStrokeColor(RULE);c.setLineWidth(.35);c.line(M,H-M+3*mm,W-M,H-M+3*mm)
        c.setFillColor(MUTED);c.setFont('Song',7.7);c.drawString(M,H-M+7*mm,self.current)
        c.setFont('Latin',9);c.drawCentredString(W/2,M-7*mm,str(doc.page));c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Title):
            self.canv.bookmarkHorizontalAbsolute(f.key,self.frame._y+f.height)
            level=min(f.level,self.outline_level+1);self.canv.addOutlineEntry(f.plain,f.key,level=level,closed=level>0);self.outline_level=level
            self.headings.append({'title':f.plain,'key':f.key,'level':level,'page':self.page})
            if f.level==0:self.current=f.plain;self.sections[f.plain]=self.page
            if f.level==0 and f.toc:self.notify('TOCEntry',(0,inline(f.plain),self.page,f.key))
def build():
    text=INPUT.read_text(encoding='utf-8');text=text[text.index('# 阅读说明'):]
    story=[Spacer(1,43*mm),P('知识与决策','cover'),P('*Knowledge and Decisions*','coverSmall'),Spacer(1,13*mm),P('托马斯·索维尔','coverSmall'),Spacer(1,37*mm),P('中文校订版 · 2026年11月','meta'),PageBreak()]
    current='';heading_no=0;toc_added=False;original_toc=False;index_subentries=0
    for raw_block in re.split(r'\n\s*\n',text):
        probe=re.sub(r'<!--.*?-->|<a id="[^"]+"></a>','',raw_block,flags=re.S).lstrip(' \t\r\n')
        index_indent=len(probe)-len(probe.lstrip('\u3000'))
        block=raw_block.strip()
        if not block:continue
        visible=re.sub(r'<!--.*?-->|<a id="[^"]+"></a>','',block,flags=re.S).strip()
        if not visible:
            names=re.findall(r'<a id="([^"]+)"></a>',block)
            for name in names:anchors[name]+=1
            if names:story.append(Anchor(names))
            continue
        h=re.match(r'^(#{1,4}) (.+)$',visible,re.S)
        if h:
            level=len(h[1])-1;title=h[2];heading_no+=1
            if level==0:
                if title=='版权及原书目录' and not toc_added:
                    story.append(PageBreak());story.append(Title('阅读目录','reading-toc',toc=False))
                    toc=TableOfContents();toc.levelStyles=[style('toc',fontSize=10,leading=15.5,spaceAfter=4,leftIndent=0,rightIndent=24,alignment=TA_LEFT)]
                    story.append(toc);toc_added=True
                if title!='阅读说明':story.append(PageBreak())
                if title.startswith(('第一部分','第二部分')):story.append(Spacer(1,48*mm))
                current=title
                original_toc=False
            if current=='版权及原书目录' and title=='原书目录':original_toc=True
            # Keep embedded provenance anchors in merged title text.
            title_with_meta=block[block.index(h[1]+' ')+len(h[1])+1:] if block.startswith(h[1]+' ') else title
            story.append(Title(title_with_meta,f'heading-{heading_no:03d}',level,toc=title!='阅读说明'))
            continue
        note=re.match(r'^\[\^([^\]]+)\]: (.*)$',visible,re.S)
        if note:
            nid,content=note.groups();defs[nid]+=1
            names=re.findall(r'<a id="([^"]+)"></a>',block)
            for name in names:anchors[name]+=1
            prefix=''.join(f'<a name="{name}"/>' for name in names)
            label=nid.rsplit('-',1)[1]
            xml=prefix+f'<a name="note-{nid}"/><link href="#ref-{nid}-1" color="{LINK}">{runs(label)}</link>{runs(". ")}{inline(content)}'
            units.append(label+'. '+plain(content));story.append(Paragraph(xml,ST['note']));continue
        im=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',visible)
        if im:
            caption,filename=im.groups();p=ROOT/filename
            with PILImage.open(p) as image:w,h=image.size
            maxh=12*mm if '003-03' in filename else 82*mm if '001-01' in filename else 148*mm
            ratio=min(WIDTH/w,maxh/h);pic=Image(str(p),width=w*ratio,height=h*ratio);pic.hAlign='LEFT'
            story.append(KeepTogether([pic,Spacer(1,3*mm),P(caption,'meta')]));images.append(filename);continue
        # Comments can precede text inside the same block; inline() retains page destinations.
        if visible.startswith('>'):
            cleaned=re.sub(r'(?m)^> ?','',block)
            which='editorial' if '【译校说明】' in cleaned else 'quote'
        else:cleaned=block;which='index' if current=='索引' else 'original_toc' if original_toc else 'body'
        if current=='索引' and index_indent:
            index_subentries+=1;story.append(P(cleaned,which,leftIndent=12*index_indent))
        else:story.append(P(cleaned,which))
    assert set(refs)==set(defs),(set(refs)-set(defs),set(defs)-set(refs))
    assert len(defs)==1001 and all(v==1 for v in defs.values())
    assert set(anchors)=={f'pdf-{p:03d}' for p in range(1,569)} and all(v==1 for v in anchors.values())
    assert not missing,missing
    assert index_subentries==len(re.findall(r'(?m)^\u3000',text))
    doc=Book();doc.multiBuild(story,maxPasses=6,canvasmaker=NamedCanvas)
    from pypdf import PdfReader
    reader=PdfReader(str(OUT))
    manifest={'pdf':str(OUT.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'bytes':OUT.stat().st_size,'pages':len(reader.pages),'markdown_sha256':hashlib.sha256(INPUT.read_bytes()).hexdigest(),'original_notes':len(defs),'note_references':sum(refs.values()),'source_anchors':len(anchors),'index_subentries':index_subentries,'images':images,'missing_glyphs':dict(missing),'headings':doc.headings,'sections':doc.sections,'layout_passes':doc.pass_no,'text_units':units}
    manifest['rendered_text_units']=len(manifest.pop('text_units'))
    (ROOT/'reports/PDF构建清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:manifest[k] for k in ['pdf','pages','bytes','original_notes','source_anchors','missing_glyphs']},ensure_ascii=False),flush=True)
if __name__=='__main__':build()
