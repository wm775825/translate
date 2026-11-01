"""Check retained book inputs and references without rebuilding or changing them."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
VOLUMES = ['第一卷','第二卷','第三卷','第四卷','第五卷','第六卷','第七卷','第八卷','第九卷']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--migration-baseline', action='store_true',
                        help='另外与首次清理前的内容哈希比较；后续正常修订不需要此选项。')
    args = parser.parse_args()
    errors = []
    counts = []
    optional_pdfs = set()
    for n, name in enumerate(VOLUMES, 1):
        folder = ROOT / name
        progress = json.loads((folder / '翻译进度.json').read_text(encoding='utf-8'))
        optional_pdfs.add((folder / progress['current_pdf']).resolve())
        chapters = [s for s in progress['chapters'] if s['status'] == 'translated']
        items = chapters + [s for s in progress.get('other_sections', []) if s['status'] == 'translated']
        gaps = [s for s in progress['chapters'] if s['status'] == 'source_missing']
        notes = 0
        for section in items + gaps:
            path = folder / section['chinese_file']
            if not path.is_file():
                errors.append(f'缺少分章稿：{path.relative_to(ROOT)}')
                continue
            text = path.read_text(encoding='utf-8-sig')
            calls = re.findall(r'\[\^([^\]]+)\](?!:)', text)
            definitions = re.findall(r'^\[\^([^\]]+)\]:', text, re.M)
            if set(calls) != set(definitions) or len(definitions) != len(set(definitions)):
                errors.append(f'注释引用或定义异常：{path.relative_to(ROOT)}')
            notes += len(definitions)
            if '\ufffd' in text or '(cid:' in text:
                errors.append(f'译稿存在提取占位字符：{path.relative_to(ROOT)}')
        current = folder / progress['complete_chinese_file']
        if not current.is_file():
            errors.append(f'缺少正式合订稿：{current}')
        source_name = progress.get('source_pdf')
        if source_name and progress.get('source_sha256'):
            source = ROOT / source_name
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != progress['source_sha256']:
                errors.append(f'原书文件缺失或改变：{source_name}')
        if n > 1:
            pages = ROOT / f'data/volume{n}/pages.json'
            note_data = ROOT / f'data/volume{n}/notes.json'
            index = ROOT / f'data/volume{n}/index-entries.json'
            for p in [pages, note_data, index]:
                if not p.is_file():
                    errors.append(f'缺少构建数据：{p.relative_to(ROOT)}')
        counts.append({'volume': n, 'translated_chapters': len(chapters),
                       'missing_chapters': [s['chapter'] for s in gaps], 'notes': notes})
    # Angle-wrapped local links are the convention used by project reading files.
    for folder in [ROOT] + [ROOT / v for v in VOLUMES]:
        for path in folder.glob('*.md'):
            text = path.read_text(encoding='utf-8-sig')
            for link in re.findall(r'\]\(<([^>]+)>\)', text):
                if re.match(r'^[a-zA-Z]+://', link) or link.startswith('#'):
                    continue
                target = (path.parent / unquote(link.split('#')[0])).resolve()
                if not target.exists() and target not in optional_pdfs:
                    errors.append(f'本地链接失效：{path.relative_to(ROOT)} → {link}')
            for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
                if re.match(r'^[a-zA-Z]+://', image):
                    continue
                target = path.parent / unquote(image.strip('<>'))
                if not target.is_file():
                    errors.append(f'图片引用失效：{path.relative_to(ROOT)} → {image}')
    protected_count = 0
    if args.migration_baseline:
        baseline = json.loads((ROOT / 'reports/pre-git/protected-content.json').read_text(encoding='utf-8'))
        for item in baseline:
            p = ROOT / item['path']
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
                errors.append(f'清理前后内容不一致：{item["path"]}')
            protected_count += 1
    result = {'all_checks_passed': not errors, 'books': counts,
              'translated_chapters': sum(c['translated_chapters'] for c in counts),
              'migration_content_hashes_checked': protected_count,
              'errors': sorted(set(errors))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
