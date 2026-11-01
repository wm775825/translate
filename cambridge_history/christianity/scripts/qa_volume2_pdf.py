from pathlib import Path
from environment import poppler_tool
import json,re,unicodedata,collections,subprocess,hashlib,xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'tmp/pdfs-volume2'
P=Path(json.loads((T/'build-manifest.json').read_text(encoding='utf-8'))['output'])
tool=poppler_tool('pdftotext')
subprocess.run([str(tool),'-raw','-enc','UTF-8',str(P),str(T/'raw-text.txt')],check=True)
subprocess.run([str(tool),'-bbox','-enc','UTF-8',str(P),str(T/'word-bounds.html')],check=True)
reader=PdfReader(P)
manifest=json.loads((T/'build-manifest.json').read_text(encoding='utf-8'))
expected=json.loads((T/'expected-text.json').read_text(encoding='utf-8'))
pages=(T/'raw-text.txt').read_text(encoding='utf-8').split('\f')
body=[]
headers=set(v['title'] for v in manifest['sections'].values())
for page in pages:
    ls=page.strip().splitlines()
    if ls and re.fullmatch(r'\d+',ls[-1]):ls.pop()
    if ls and ls[-1].strip() in headers:ls.pop()
    body.append('\n'.join(ls))
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC',s) if unicodedata.category(c)[0] in 'LN')
actual=norm('\n'.join(body));not_found=[]
# Headers are included in the build's expected list only for a character census.
# For paragraph coverage use those preceding the final page-header list.
paragraphs=expected[:len(expected)-(len(reader.pages)-1)]
for k,text in enumerate(paragraphs):
    q=norm(text)
    if len(q)>=8 and q not in actual:not_found.append(dict(number=k,text=text))

objects={p.indirect_reference.idnum:i+1 for i,p in enumerate(reader.pages)}
links=0;bad_links=[];outside=[]
for n,p in enumerate(reader.pages,1):
    for ref in p.get('/Annots',[]):
        a=ref.get_object()
        if a.get('/Subtype')!='/Link':continue
        links+=1
        dest=a.get('/Dest') or a.get('/A',{}).get('/D')
        if isinstance(dest,list) and getattr(dest[0],'idnum',None) not in objects:bad_links.append((n,str(dest)))
        rect=a.get('/Rect',[])
        if len(rect)==4 and (float(rect[0])<-1 or float(rect[2])>499.9 or float(rect[1])<-1 or float(rect[3])>709.7):outside.append((n,list(map(float,rect))))

xml=ET.parse(T/'word-bounds.html')
bad_bounds=[];edge_words=[]
for n,page in enumerate(xml.getroot().iter('{http://www.w3.org/1999/xhtml}page'),1):
    w=float(page.attrib['width']);h=float(page.attrib['height'])
    for word in page.iter('{http://www.w3.org/1999/xhtml}word'):
        x0,y0,x1,y1=[float(word.attrib[k]) for k in ['xMin','yMin','xMax','yMax']]
        if x0<0 or y0<0 or x1>w+.5 or y1>h+.5:bad_bounds.append((n,word.text,[x0,y0,x1,y1]))
        if x0<51 or x1>w-51:edge_words.append((n,word.text,[x0,y0,x1,y1]))
out=dict(pages=len(reader.pages),sha256=hashlib.sha256(P.read_bytes()).hexdigest(),
         text_fragments_checked=sum(len(norm(s))>=8 for s in paragraphs),links=links,missing_paragraphs=not_found,broken_internal_links=bad_links,
         link_rectangles_outside_page=outside,words_outside_page=bad_bounds,words_outside_margins=edge_words,
         outline_roots=len(reader.outline),font_preflight=manifest['missing_glyphs'])
(T/'qa-report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('pages',out['pages'],'links',links,'missing paragraphs',len(not_found),'bad links',len(bad_links),
      'outside page',len(bad_bounds),'outside margins',len(edge_words),'outside link boxes',len(outside))
for item in not_found[:8]:print('MISSING',str(item)[:220])
for item in edge_words[:8]:print('EDGE',item)

issues = ['missing_paragraphs','broken_internal_links','link_rectangles_outside_page','words_outside_page','words_outside_margins','font_preflight']
if any(out[k] for k in issues):
    raise SystemExit('PDF校核发现问题，详见 qa-report.json')
