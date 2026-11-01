"""Small entry point for the existing nine volume-specific PDF builders."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ['第一卷','第二卷','第三卷','第四卷','第五卷','第六卷','第七卷','第八卷','第九卷']


def run_script(filename, env=None):
    subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts' / filename)],
                   cwd=ROOT, env=env, check=True)


def collection(volume):
    """Use the saved front matter and the current approved chapter files."""
    config = json.loads((ROOT / 'data/collections.json').read_text(encoding='utf-8'))[str(volume)]
    folder = ROOT / VOLUMES[volume - 1]
    progress = json.loads((folder / '翻译进度.json').read_text(encoding='utf-8'))
    sections = progress['chapters'] + progress.get('other_sections', [])
    approved_gaps = set(progress.get('authorized_skipped_chapters', []))
    sections = sorted(
        [s for s in sections if s['status'] == 'translated' or
         (s['status'] == 'source_missing' and s.get('chapter') in approved_gaps)],
        key=lambda s: s['pdf_start'])
    header = (ROOT / config['header_file']).read_text(encoding='utf-8')
    parts = []
    for section in sections:
        text = (folder / section['chinese_file']).read_text(encoding='utf-8-sig')
        if volume in [1, 2]:
            import re
            if 'chapter' in section:
                anchor = f'chapter-{section["chapter"]:02}'
                prefix = f'ch{section["chapter"]:02}'
            else:
                anchor = section.get('key') or {
                    '结语':'conclusion','序篇':'prelude','前言':'preface',
                    '致谢':'acknowledgements','卷首资料':'frontmatter',
                    '参考文献说明与章目':'bibliography','索引':'index'
                }.get(section.get('section'), section.get('section'))
                if not anchor:
                    raise ValueError(f'缺少章节锚点：{section}')
                prefix = anchor
            text = re.sub(r'\[\^(\d+)\]', lambda m: f'[^{prefix}-{m[1]}]', text)
            text = f'<a id="{anchor}"></a>\n\n' + text
        parts.append(text)
    result = header + '\n\n---\n\n' + '\n\n---\n\n'.join(parts)
    if volume in [1, 2]:
        result += '\n'
    return result, folder / progress['complete_chinese_file']


def main():
    parser = argparse.ArgumentParser(description='九卷阅读版维护入口；源译文为各卷分章Markdown。')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['build', 'qa', 'assemble']:
        sub = commands.add_parser(name)
        sub.add_argument('volume', type=int, choices=range(1, 10))
        if name == 'build':
            sub.add_argument('--output-dir', default='tmp/build-output',
                             help='默认导出待核验目录；不会自动替换正式PDF。')
        if name == 'assemble':
            sub.add_argument('--output', help='默认写到tmp/collections，不覆盖正式合订稿。')
            sub.add_argument('--check', action='store_true', help='只比较与现有合订稿是否一致。')
    render = commands.add_parser('render')
    render.add_argument('volume', type=int, choices=range(1, 10))
    render.add_argument('--pages', type=int, nargs='+')
    render.add_argument('--contacts', action='store_true')
    args = parser.parse_args()
    if args.command in ['build', 'qa']:
        name = ('build_chinese_pdf.py' if args.command == 'build' else 'qa_chinese_pdf.py') if args.volume == 1 else \
               f'{args.command}_volume{args.volume}_pdf.py'
        env = os.environ.copy()
        if args.command == 'build':
            env['CAMBRIDGE_PDF_OUTPUT_DIR'] = str((ROOT / args.output_dir).resolve())
        run_script(name, env)
    elif args.command == 'assemble':
        text, current = collection(args.volume)
        if args.check:
            if text != current.read_text(encoding='utf-8'):
                raise SystemExit('分章稿与合订稿存在差异；请先检查译文及卷首说明。')
            print(f'第{args.volume}卷：分章稿与正式合订稿一致。')
        else:
            target = Path(args.output) if args.output else ROOT / 'tmp/collections' / current.name
            target = target.resolve()
            if target == current.resolve():
                raise SystemExit('请先导出待核验合订稿；核对后再替换正式文件并更新校核记录。')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
            print(target)
    else:
        command = [sys.executable, '-X', 'utf8', str(ROOT / 'scripts/render_pdf.py'), str(args.volume)]
        if args.pages: command += ['--pages', *map(str, args.pages)]
        if args.contacts: command.append('--contacts')
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
