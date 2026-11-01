"""Render the actual PDF named in its current build manifest."""
import argparse
import concurrent.futures
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from environment import font_path, poppler_tool

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('volume', type=int, choices=range(1, 10))
parser.add_argument('--pages', type=int, nargs='+')
parser.add_argument('--contacts', action='store_true')
args = parser.parse_args()
work = ROOT / ('tmp/pdfs' if args.volume == 1 else f'tmp/pdfs-volume{args.volume}')
manifest = json.loads((work / 'build-manifest.json').read_text(encoding='utf-8'))
pdf = Path(manifest['output'])
count = len(PdfReader(pdf).pages)
dest = work / 'visual'
dest.mkdir(parents=True, exist_ok=True)
tool = poppler_tool('pdftoppm')
pages = sorted(set(args.pages or [1, 2, 3, count]))
if any(n < 1 or n > count for n in pages):
    raise SystemExit('抽查页码不在PDF页数范围内。')

def render(page):
    subprocess.run([str(tool), '-f', str(page), '-l', str(page), '-scale-to', '1600',
                    '-singlefile', '-png', str(pdf), str(dest / f'page-{page:03}')], check=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(render, pages))
contacts = []
if args.contacts:
    thumbs = dest / 'thumbs'
    thumbs.mkdir(exist_ok=True)
    subprocess.run([str(tool), '-r', '24', '-png', str(pdf), str(thumbs / 'page')], check=True)
    files = sorted(thumbs.glob('page-*.png'))
    if len(files) != count:
        raise SystemExit('缩略图数量与PDF页数不一致；请使用新的构建工作目录。')
    font = ImageFont.truetype(str(font_path('arial.ttf')), 12)
    for start in range(0, count, 64):
        canvas = Image.new('RGB', (1360, 2000), '#e3e6e8')
        draw = ImageDraw.Draw(canvas)
        for j, filename in enumerate(files[start:start + 64]):
            with Image.open(filename) as source:
                thumb = source.convert('RGB')
            thumb.thumbnail((156, 223))
            canvas.paste(thumb, ((j % 8) * 170 + (170 - thumb.width) // 2, (j // 8) * 250 + 18))
            draw.text(((j % 8) * 170 + 6, (j // 8) * 250 + 2), str(start + j + 1), font=font, fill='black')
        target = dest / f'contact-{start // 64 + 1:02}.png'
        canvas.save(target)
        contacts.append(target.name)
(dest / 'render-plan.json').write_text(json.dumps({
    'pdf': str(pdf), 'pages': count, 'enlarged_pages_rendered': pages,
    'contact_sheets_rendered': contacts,
    'review_status': 'rendered_only_not_yet_visually_reviewed'
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'已渲染{len(pages)}个放大页、{len(contacts)}张联系表；仍须实际查看。')
