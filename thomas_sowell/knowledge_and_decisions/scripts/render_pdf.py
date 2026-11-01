"""Create all-page contact sheets and selected full-size pages inside this book."""
import argparse,json,subprocess,shutil,os
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
POPPLER=Path(os.environ.get('TRANSLATIONS_POPPLER') or shutil.which('pdftoppm') or Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pages',nargs='*',type=int,default=[]);ap.add_argument('--contacts',action='store_true');args=ap.parse_args()
    m=json.loads((ROOT/'reports/PDF构建清单.json').read_text(encoding='utf-8'));pdf=ROOT/m['pdf'];dest=ROOT/'tmp/pdfs/render';dest.mkdir(parents=True,exist_ok=True)
    if args.contacts:
        thumbs=dest/'thumbnails';thumbs.mkdir(exist_ok=True)
        subprocess.run([str(POPPLER),'-scale-to','310','-png',str(pdf),str(thumbs/'p')],check=True)
        # A later layout may have fewer pages. Remove only the obsolete generated
        # thumbnail and contact files, after checking their absolute locations.
        for f in thumbs.glob('p-*.png'):
            if int(f.stem.rsplit('-',1)[1])>m['pages']:
                assert f.resolve().is_relative_to((ROOT/'tmp/pdfs/render').resolve());f.unlink()
        for f in dest.glob('contact-*.png'):
            assert f.resolve().is_relative_to((ROOT/'tmp/pdfs/render').resolve());f.unlink()
        files=sorted(thumbs.glob('p-*.png'));assert len(files)==m['pages']
        for start in range(0,len(files),36):
            sheet=Image.new('RGB',(6*235,6*340),'#dfe3e6');draw=ImageDraw.Draw(sheet)
            for j,f in enumerate(files[start:start+36]):
                im=Image.open(f).convert('RGB');im.thumbnail((225,310));x=(j%6)*235+(235-im.width)//2;y=(j//6)*340+22
                sheet.paste(im,(x,y));draw.text(((j%6)*235+8,(j//6)*340+5),str(start+j+1),fill='black')
            out=dest/f'contact-{start+1:03d}-{min(start+36,len(files)):03d}.png';sheet.save(out);print(out.name,flush=True)
    for p in args.pages:
        subprocess.run([str(POPPLER),'-f',str(p),'-l',str(p),'-scale-to','1600','-png','-singlefile',str(pdf),str(dest/f'page-{p:03d}')],check=True)
        print(f'page-{p:03d}.png',flush=True)
if __name__=='__main__':main()
