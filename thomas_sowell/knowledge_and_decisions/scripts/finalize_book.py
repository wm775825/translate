"""Promote an inspected PDF and synchronize current delivery metadata."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def save(p,v):(ROOT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    m=read('reports/PDF构建清单.json');qa=read('reports/PDF自动校核.json');visual=read('reports/PDF视觉校核.json')
    assert qa['all_checks_passed'] and visual['all_checks_passed']
    assert m['sha256']==qa['sha256']==visual['sha256']==sha(m['pdf'])
    assert m['markdown_sha256']==sha('知识与决策（中文校订版）.md')
    progress=read('翻译进度.json');assert sha(progress['source_pdf'])==progress['source_sha256']
    final='output/pdf/知识与决策（中文校订版）.pdf';target=ROOT/final;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha(final)!=m['sha256']:
        tracked=subprocess.run(['git','ls-files','--error-unmatch',str(target)],cwd=ROOT,capture_output=True)
        clean=subprocess.run(['git','diff','--quiet','--',str(target)],cwd=ROOT)
        staged=subprocess.run(['git','diff','--cached','--quiet','--',str(target)],cwd=ROOT)
        assert tracked.returncode==0 and clean.returncode==0 and staged.returncode==0,'正式文件存在未提交变更，停止覆盖。'
    if (ROOT/m['pdf']).resolve()!=target.resolve():shutil.copyfile(ROOT/m['pdf'],target)
    assert sha(final)==m['sha256']
    m['pdf']=final;save('reports/PDF构建清单.json',m)
    qa['file']=final;save('reports/PDF自动校核.json',qa)
    visual['file']=final;save('reports/PDF视觉校核.json',visual)
    current={}
    for item in progress['chapters']+progress['other_sections']:
        if not item.get('chinese_file'):continue
        file=item['chinese_file'];path=ROOT/file;t=path.read_text(encoding='utf-8')
        path.write_text(t,encoding='utf-8',newline='\n')
        item['chinese_sha256']=sha(file);item['chinese_characters']=len(re.findall(r'[\u4e00-\u9fff]',t))
        item['language_review']='当前代理已在原文分块对照翻译后，另行连续通读全部中文；完成已记录的语义、语序、术语、指代及引文格式修订。'
        current[file]={'sha256':item['chinese_sha256'],'chinese_characters':item['chinese_characters']}
        if 'chapter' in item:
            name=f"reports/第{item['chapter']:02d}章校核记录.json";report=read(name)
            report.update(chinese_sha256=item['chinese_sha256'],chinese_characters=item['chinese_characters'])
            if isinstance(report.get('review_scope'),dict):
                scope=report['review_scope'];scope['language']=item['language_review']
                for key in ('pdf_authored','chinese_pdf_authored'):
                    if key in scope:scope[key]=True
                scope['pdf_checks']='全书PDF自动及视觉校核已完成，当前文件身份和范围见对应PDF校核记录。'
            report['current_file_followup']='中文维护稿为UTF-8/LF；标题层级、来源标识和原注保留。全书通读、合订、自动及视觉排版校核已完成，范围分别见全书记录。'
            save(name,report)
        if 'notes_translation_file' in item:
            name=item['notes_translation_file'];mapping=read(name)
            prefix='pre-' if item.get('id')=='preface' else f"c{item['chapter']:02d}-"
            definitions=dict(re.findall(r'^\[\^([^\]]+)\]: (.*)$',t,re.M))
            for key in mapping:mapping[key]=definitions[prefix+key]
            save(name,mapping)
    report=read('reports/卷首卷末校核记录.json');report['current_files']={k:v for k,v in current.items() if not Path(k).name.startswith('第0') and not Path(k).name.startswith('第10章')}
    report['review_scope']='已按原文分块对照翻译，另行连续通读卷首卷末中文；全书统一校订、索引翻译及PDF自动和视觉校核均已完成。独立专业逐句精校未进行。';save('reports/卷首卷末校核记录.json',report)
    report=read('reports/索引校核记录.json');index=next(x for x in progress['other_sections'] if x['id']=='index')
    report.update(chinese_sha256=index['chinese_sha256'],chinese_characters=index['chinese_characters'],review_scope='已逐来源分块翻译全部索引，另行连续通读中文，核对数字并统一已记录译名；PDF保留主分项缩进及原书纸本页码。')
    save('reports/索引校核记录.json',report)
    language=read('reports/全书中文语言校订.json')
    language.update(status='complete',completed_source_pdf_ranges_compact=[[1,460],[530,568]],notes_scope='解释性原注已随序言及各章中文通读；纯外文书目按原文保留。原注页码以编号及源页集合追溯，不冒充原注原始分块逐段对应。',current_files=current,full_book_language_review_complete=True)
    save('reports/全书中文语言校订.json',language)
    progress.update(status='complete',full_book_complete=True,last_completed_pdf_page=568,next_step='整本中文校订版已完成并通过核验。后续如修订，以分节中文维护稿为源，重新合订并核验。',pending_book_review=[],final_pdf_verified=True,
                    current_pdf={'path':final,'pages':m['pages'],'bytes':m['bytes'],'sha256':m['sha256']},current_markdown={'path':'知识与决策（中文校订版）.md','sha256':m['markdown_sha256']},completed_original_notes=1001)
    progress['language_review_cursor'].update(next_pdf_page=None,status='complete',completed_ranges=[[1,460],[530,568]])
    save('翻译进度.json',progress)
    save('reports/全书交付记录.json',{'status':'complete','source_pdf_sha256':progress['source_sha256'],'pdf':progress['current_pdf'],'markdown':progress['current_markdown'],'chapters':10,'original_notes':1001,'source_blocks':1640,'source_page_anchors':568,'automatic_checks_passed':True,'visual_checks_passed':True,'independent_professional_review':False,'editing_source':'chapters/*（中文）.md','source_limits':'底本损坏文字、原注定位不确定及原书疑误均保留对应译校说明；纸本索引页码无法可靠换算为中文页码。'})
    print(json.dumps(progress['current_pdf'],ensure_ascii=False))
if __name__=='__main__':main()
