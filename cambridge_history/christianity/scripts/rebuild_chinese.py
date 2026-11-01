from pathlib import Path
import json,re

r=Path(__file__).resolve().parents[1]/'第一卷'
d=json.loads((r/'翻译进度.json').read_text(encoding='utf-8-sig'))
items=[]
for c in d['chapters']:
    if c['status']=='translated':
        items.append((c['pdf_start'],f'chapter-{c["chapter"]:02}',f'ch{c["chapter"]:02}',f'第{c["chapter"]}章 {c["title_zh"]}',c['chinese_file']))
for c in d.get('other_sections',[]):
    if c['status']=='translated':
        key=c.get('key', {'结语':'conclusion','序篇':'prelude','前言':'preface','致谢':'acknowledgements','卷首资料':'frontmatter','参考文献说明与章目':'bibliography','索引':'index'}.get(c['section'],c['section']))
        items.append((c['pdf_start'],key,key,c['title_zh'],c['chinese_file']))
items.sort()
pending='、'.join(d['other_sections_pending'])
notice=f'32个编号章节已译出；全卷尚未完成，仍待补齐：{pending}。' if pending else '全卷中文译稿。正文、引文与解释性脚注译为中文；参考文献作者名、题名、刊名及定位保留原文。'
head='# 剑桥基督教史 第一卷：起源至君士坦丁\n\n## 中文译稿'+('（持续更新）' if pending else '')+'\n\n'+notice+'\n\n## 目录\n\n'
parts=[head+'\n'.join(f'- [{title}](#{anchor})' for _,anchor,_,title,_ in items)]
total=0
for _,anchor,prefix,title,file in items:
    s=(r/file).read_text(encoding='utf-8-sig')
    refs=re.findall(r'\[\^(\d+)\](?!:)',s)
    defs=re.findall(r'^\[\^(\d+)\]:',s,re.M)
    assert refs==defs==list(map(str,range(1,len(defs)+1))), (file,refs,defs)
    assert '\ufffd' not in s and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',s),file
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',s)+re.findall(r'\]\(<([^>]+)>\)',s):
        assert (r/target).exists(),(file,target)
    parts.append(f'<a id="{anchor}"></a>\n\n'+re.sub(r'\[\^(\d+)\]',lambda m:f'[^{prefix}-{m[1]}]',s))
    total+=len(defs)
out='\n\n---\n\n'.join(parts)+'\n'
refs=re.findall(r'\[\^([^\]]+)\](?!:)',out);defs=re.findall(r'^\[\^([^\]]+)\]:',out,re.M)
assert len(refs)==len(set(refs))==len(defs)==len(set(defs)) and set(refs)==set(defs)
for filename in dict.fromkeys(['01 起源至君士坦丁（中文全译）.md', '01 起源至君士坦丁（中文全译）.md']):
    (r/filename).write_text(out,encoding='utf-8')
print(f'Assembled {len(items)} sections; {total} numeric source footnotes; pending: {pending}')
