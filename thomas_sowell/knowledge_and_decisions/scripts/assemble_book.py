"""Assemble the current section drafts; never import the old translation chunks."""
import collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
SOURCE=re.compile(r'<!-- source-id:\s*(p\d+-\d+).*?-->')
META=re.compile(r'<a id="[^"]+"></a>|<!--[^>]*-->')
TAIL=re.compile(r'((?:\s|<a id="[^"]+"></a>|<!--[^>]*-->)*)\Z')

def merge_at(text,source_id):
    marker=next(m for m in SOURCE.finditer(text) if m[1]==source_id)
    left=text[:marker.start()];right=text[marker.end():]
    tail=TAIL.search(left);metadata=''.join(META.findall(tail[1]))+marker[0]
    left=left[:tail.start()].rstrip();right=right.lstrip()
    while right.startswith('<!--'):
        end=right.index('-->')+3;metadata+=right[:end];right=right[end:].lstrip()
    if right.startswith('> '):right=right[2:]
    separator=' ' if left and right and left[-1].isascii() and left[-1].isalnum() and right[0].isascii() and right[0].isalnum() else ''
    return left+metadata+separator+right

def normalized_prose(t):
    t=re.sub(r'<!--.*?-->|<a id="[^"]+"></a>','',t,flags=re.S)
    return re.sub(r'\s|(?m:^> )','',t)

READING='''# 阅读说明

本译本依据所附英文电子底本，收入十章正文、1996年版序言、致谢、原书版权与目录、全部1001条原注、索引、封底及电子版导航。原书正文初版于1980年，序言写于1996年；文中“今天”“目前”、统计和机构情况均保留原有历史时点。

本译稿由AI翻译并复核，逐段对照原文，另行通读全部中文，并完成术语对齐及重点复核；未经独立专业译者逐句精校。作者的论断保留原有归属与语气。底本的损坏、疑误及据可见文字重建之处，以译校说明标出。

原注集中排在书后，保留原编号；正文注号与原注编号可往返跳转。书目中的作者、外文题名及出版定位保留原文，解释性文字译为中文。索引沿用原书字母顺序，词目附英文，数字指原书纸本页码；底本未保留纸本逐页边界，故可按中英文词目全文检索。
'''

def assemble():
    progress=read('翻译进度.json');notes=read('data/notes.json');layout=read('data/排版接续.json')
    items=sorted([x for x in progress['chapters']+progress['other_sections'] if x.get('chinese_file')],key=lambda x:x['pdf_start'])
    texts={};definitions=[];groups=[];source_ids=[];note_pages=set()
    for item in items:
        file=item['chinese_file'];t=(ROOT/file).read_text(encoding='utf-8')
        source_ids+=SOURCE.findall(t)
        defs=re.findall(r'^\[\^([^\]]+)\]: (.*)$',t,re.M)
        if defs:
            group='preface' if item.get('id')=='preface' else f"chapter{item['chapter']}"
            prefix='pre-' if group=='preface' else f"c{item['chapter']:02d}-"
            bynumber={str(n['number']):n for n in notes[group]}
            assert len(defs)==len(bynumber),(group,len(defs),len(bynumber))
            for nid,content in defs:
                assert nid.startswith(prefix),nid
                entry=bynumber[nid[len(prefix):]];definitions.append((nid,content,entry['pdf_pages']))
            groups.append((item['title'],defs))
            t=re.split(r'\n## (?:本章|序言)原注',t)[0].rstrip()+'\n'
        before=t
        for q in layout['joins']:
            if q['file']==file:t=merge_at(t,q['source_id'])
        assert collections.Counter(SOURCE.findall(before))==collections.Counter(SOURCE.findall(t)),file
        assert normalized_prose(before)==normalized_prose(t),file
        texts[file]=t
    assert len(definitions)==1001 and len({d[0] for d in definitions})==1001
    front=next(x['chinese_file'] for x in items if x.get('id')=='front')
    texts[front]=texts[front].replace('<!-- source-image: assets/source-p001-01.jpg; original cover lettering translated -->','<!-- source-image: assets/source-p001-01.jpg; original cover lettering translated -->\n\n![原书封面](assets/source-p001-01.jpg)')
    texts[front]=texts[front].replace('<!-- source-id: p003-06 -->','![原版出版标志](assets/source-p003-03.jpg)\n\n<!-- source-id: p003-06 -->')
    back=next(x['chinese_file'] for x in items if x.get('id')=='back-cover')
    texts[back]+='\n![原书封底](assets/source-p566-01.jpg)\n'
    parts=['# 知识与决策\n\n托马斯·索维尔\n\n*Knowledge and Decisions*\n\n中文校订版\n',READING]
    for item in items:
        if item['pdf_start']>=530:continue
        parts.append(texts[item['chinese_file']])
    parts.append('# 原注\n\n原注编号对应各章；点击编号返回正文。\n')
    definition_map={nid:(content,pages) for nid,content,pages in definitions}
    for title,defs in groups:
        parts.append('## '+title+'原注\n')
        for nid,_ in defs:
            content,pages=definition_map[nid]
            anchors=[]
            for page in pages:
                if page not in note_pages:
                    anchors.append(f'<a id="pdf-{page:03d}"></a><!-- PDF physical page {page}; note-level mapping -->')
                    note_pages.add(page)
            parts.append('\n'.join(anchors+[f'<!-- original-note-id: {nid}; source-pdf-pages: {",".join(map(str,pages))} -->',f'[^{nid}]: {content}'])+'\n')
    assert note_pages==set(range(461,530))
    for item in items:
        if item['pdf_start']>=530:parts.append(texts[item['chinese_file']])
    out='\n\n'.join(x.strip() for x in parts)+'\n'
    assert collections.Counter(SOURCE.findall(out))==collections.Counter(source_ids)
    anchors=re.findall(r'<a id="pdf-(\d+)"></a>',out)
    assert len(anchors)==568 and {int(p) for p in anchors}==set(range(1,569))
    path=ROOT/'知识与决策（中文校订版）.md';path.write_text(out,encoding='utf-8',newline='\n')
    save('reports/合订记录.json',{'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'editing_source':'chapters/*（中文）.md','source_ids':len(source_ids),'source_anchors':568,'original_notes':1001,'paragraph_joins':len(layout['joins']),'source_note_mapping':'原注页锚按原注覆盖页集合，跳到该页首条关联原注，不冒充逐字定位。','source_images_included':['assets/source-p001-01.jpg','assets/source-p003-03.jpg','assets/source-p566-01.jpg']})
    print(json.dumps({'markdown':path.name,'source_ids':len(source_ids),'anchors':len(anchors),'notes':len(definitions),'joins':len(layout['joins'])},ensure_ascii=False))
    return path
if __name__=='__main__':assemble()
