"""Local tool discovery shared by book import, build, and QA scripts."""
import os
import shutil
import sys
from pathlib import Path


def font_path(filename):
    directory = os.environ.get('CAMBRIDGE_FONT_DIR')
    candidates = ([Path(directory)] if directory else []) + [
        Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    ]
    for folder in candidates:
        if (folder / filename).is_file():
            return folder / filename
    raise FileNotFoundError(
        f'缺少字体 {filename}；请设置 CAMBRIDGE_FONT_DIR 指向所需字体目录。'
    )


def poppler_tool(name):
    override = os.environ.get('CAMBRIDGE_' + name.upper())
    if override:
        path = Path(override)
        if not path.is_file():
            raise FileNotFoundError(f'配置的{name}不存在：{path}')
        return path
    found = shutil.which(name)
    if found:
        return Path(found)
    # Codex bundled Python and native tools share the dependencies directory.
    native = Path(sys.executable).resolve().parent.parent / 'native/poppler'
    executable = name + ('.exe' if os.name == 'nt' else '')
    for folder in [native / 'Library/bin', native / 'bin']:
        if (folder / executable).is_file():
            return folder / executable
    raise FileNotFoundError(
        f'找不到{name}；将Poppler加入PATH，或设置 CAMBRIDGE_{name.upper()}。'
    )


def require_uninitialized(book_directory):
    if (book_directory / '翻译进度.json').exists():
        raise SystemExit('本卷已有进度，禁止用首次转换脚本重置现有译文。')
