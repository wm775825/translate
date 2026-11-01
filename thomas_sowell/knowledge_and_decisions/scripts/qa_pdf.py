"""Verify the actual rendered PDF, its text, destinations, images and geometry."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
import pdfplumber
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
def norm(t):return re.sub(r'\s+','',unicodedata.normalize('NFC',t))
def expected_units(markdown):
    """Independently read visible Markdown instead of storing another text copy."""
    units=[]
    for block in re.split(r'\n\s*\n',markdown):
        s=re.sub(r'<!--.*?-->|<a id="[^"]+"></a>','',block,flags=re.S).strip()
        if not s:continue
        note=re.match(r'^\[\^([^\]]+)\]: (.*)$',s,re.S)
        if note:s=note[1].rsplit('-',1)[1]+'. '+note[2]
        s=re.sub(r'(?m)^#{1,6} |^> ?','',s)
        s=re.sub(r'!\[([^\]]*)\]\([^)]+\)',r'\1',s)
        s=re.sub(r'\[\^([^\]]+)\]',lambda m:m[1].rsplit('-',1)[1],s)
        s=re.sub(r'\[([^\]]+)\]\((?:<[^>]+>|[^)]+)\)',r'\1',s)
        s=re.sub(r'\*\*([^\n]+?)\*\*',r'\1',s)
        s=re.sub(r'\*([^\n*]+?)\*',r'\1',s)
        s=re.sub(r'`([^`]+)`',r'\1',s)
        units.append(s)
    return units
def main():
    manifest=json.loads((ROOT/'reports/PDF构建清单.json').read_text(encoding='utf-8'))
    path=ROOT/manifest['pdf'];reader=PdfReader(str(path));errors=[]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256']
    assert hashlib.sha256((ROOT/'知识与决策（中文校订版）.md').read_bytes()).hexdigest()==manifest['markdown_sha256']
    destinations=reader.named_destinations
    required={f'pdf-{i:03d}' for i in range(1,569)}
    required|={f'note-{n}' for n in re.findall(r'^\[\^([^\]]+)\]:', (ROOT/'知识与决策（中文校订版）.md').read_text(encoding='utf-8'),re.M)}
    errors += [{'missing_destination':n} for n in sorted(required-set(destinations))]
    bad_dest=[]
    for key,value in destinations.items():
        page=reader.get_destination_page_number(value)
        if page is None or not 0<=page<len(reader.pages):bad_dest.append(key)
    if bad_dest:errors.append({'bad_destinations':bad_dest})
    page_refs={p.indirect_reference.idnum:i for i,p in enumerate(reader.pages)}
    links=collections.Counter();bad_links=[];bad_rects=[]
    for i,page in enumerate(reader.pages,1):
        width=float(page.mediabox.width);height=float(page.mediabox.height)
        for ref in page.get('/Annots',[]):
            a=ref.get_object()
            if a.get('/Subtype')!='/Link':continue
            rect=list(map(float,a['/Rect']))
            if min(rect)<-1 or max(rect[0::2])>width+1 or max(rect[1::2])>height+1:bad_rects.append((i,rect))
            if '/Dest' in a:d=a['/Dest'];links['internal']+=1
            elif a.get('/A',{}).get('/S')=='/GoTo':d=a['/A']['/D'];links['internal']+=1
            elif a.get('/A',{}).get('/S')=='/URI':links['external']+=1;continue
            else:continue
            if isinstance(d,(str,bytes)):
                if d not in destinations:bad_links.append((i,str(d)))
            elif not d or getattr(d[0],'idnum',None) not in page_refs:bad_links.append((i,str(d)))
    if bad_links:errors.append({'bad_links':bad_links})
    if bad_rects:errors.append({'bad_link_rectangles':bad_rects})
    text=[];bounds=[];images=0;page_stats=[]
    with pdfplumber.open(path) as pdf:
        for i,page in enumerate(pdf.pages,1):
            chars=page.chars;images+=len(page.images)
            for c in chars:
                if not c['text'].strip():continue
                if c['x0']<52.8 or c['x1']>float(page.width)-52.8 or c['top']<15 or c['bottom']>float(page.height)-15:
                    bounds.append({'page':i,'text':c['text'],'box':[round(c[k],2) for k in ['x0','top','x1','bottom']]})
            # Remove furniture so a paragraph spanning pages remains contiguous.
            body=page.crop((0,58,float(page.width),float(page.height)-55)) if i>1 else page
            extracted=body.extract_text(x_tolerance=1,y_tolerance=3) or ''
            text.append(extracted);page_stats.append({'page':i,'characters':len(extracted),'images':len(page.images)})
            page.close()
            if i%50==0:print('Checked pages',i,flush=True)
    joined=norm(''.join(text));missing_units=[]
    source_units=expected_units((ROOT/'知识与决策（中文校订版）.md').read_text(encoding='utf-8'))
    for i,unit in enumerate(source_units):
        expected=norm(unit)
        if expected and expected not in joined:missing_units.append({'unit':i,'length':len(expected),'start':unit[:100]})
    if missing_units:errors.append({'missing_text_units':missing_units})
    if bounds:errors.append({'text_out_of_bounds':bounds[:100],'total':len(bounds)})
    if images!=3:errors.append({'image_count':images,'expected':3})
    if manifest['missing_glyphs']:errors.append({'missing_glyphs':manifest['missing_glyphs']})
    if '\ufffd' in joined or '(cid:' in joined:errors.append({'replacement_or_cid':True})
    report={'file':manifest['pdf'],'sha256':manifest['sha256'],'pages':len(reader.pages),'all_checks_passed':not errors,'text_units_checked':len(source_units),'text_units_missing':len(missing_units),'named_destinations':len(destinations),'required_source_and_note_destinations':len(required),'links':dict(links),'images':images,'missing_glyphs':manifest['missing_glyphs'],'text_bounds_violations':len(bounds),'page_stats':page_stats,'errors':errors,'scope':'从当前合订Markdown独立取得可见文字，核对实际PDF的全文覆盖、字形、边界、图片及链接；视觉结果另记。'}
    (ROOT/'reports/PDF自动校核.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['page_stats','errors']},ensure_ascii=False),flush=True)
    if errors:print(json.dumps(errors,ensure_ascii=False)[:10000],flush=True);raise SystemExit(1)
if __name__=='__main__':main()
