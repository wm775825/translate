# 剑桥基督教史中文翻译

本书系位于 translations 仓库的 cambridge_history/christianity 目录，保存九卷书的原始PDF、校对后的中英文分章稿、每卷一份正式合订Markdown、图像、翻译规范、必要数据和维护脚本。现有272个编号章已译出；第九卷第20章原文缺失，保留明确说明，不计入已译章数。

阅读入口及校订范围见[九卷校订说明](<九卷校订说明.md>)。本套“中文校订版”经过译文整理、主要术语一致性检查、重点原文及版面复核，尚未经独立专业逐句精校。

## 目录与维护源

| 位置 | 内容 |
|---|---|
| 本书系目录9份原始PDF | 原书输入，保持不变 |
| 第一卷—第九卷 | 中英文分章稿、卷首卷末资料、正式合订稿、规范、进度和校核记录 |
| 各卷 assets | 原图、地图及排版所需资源 |
| data | 修正后的逐页原文、原注、中文注释、索引及人工修复数据 |
| scripts | 提取、读取、合订、PDF构建和校核工具 |
| reports | 历史检查记录及本次入库整理记录 |
| output/pdf | 本地正式中文PDF，保留但不进入Git |
| tmp | 可重新生成的构建、导出和检查文件，不进入Git |

**日常编辑以分章中文Markdown为准。** 合订稿和PDF由这些文件生成。旧“中文翻译中／持续更新”合订稿已移除；历史分块及一次性修补脚本保存在清理前完整归档中，不再作为发布输入。

## 运行环境

本次已验证Python 3.12.14、requirements.txt所列版本、Poppler，以及现有Windows字体集。安装Python依赖：

~~~powershell
python -m pip install -r requirements.txt
~~~

Poppler应提供 pdftotext、pdftoppm。工具依次查找显式环境配置、PATH和当前Codex Python旁的捆绑工具目录。可用 CAMBRIDGE_PDFTOTEXT、CAMBRIDGE_PDFTOPPM 指定程序位置。

现有版式使用宋体、黑体、楷体、Times、Arial和Segoe UI Symbol，对应构建脚本中的FONTFILES。默认从系统Windows字体目录读取，也可通过 CAMBRIDGE_FONT_DIR 指定包含这些字体文件的目录；字体文件不随仓库分发。其他系统需提供适配字体并重新核验版面。

## 常用操作

以下命令从本书系目录执行；从仓库根目录开始时，先执行 cd cambridge_history/christianity。如果python不在PATH，使用当前环境中可用解释器的完整路径。

~~~powershell
# 检查输入、原注、图片及阅读链接
python -X utf8 scripts/check_project.py

# 确认第六卷的分章稿与当前正式合订稿一致
python -X utf8 scripts/book.py assemble 6 --check

# 导出待核验合订稿，不覆盖正式文件
python -X utf8 scripts/book.py assemble 6

# 从正式分章稿构建PDF，默认写入tmp/build-output
python -X utf8 scripts/book.py build 6
python -X utf8 scripts/book.py qa 6

# 渲染后仍须实际查看图片
python -X utf8 scripts/book.py render 6 --pages 1 2 3 189 287 591 639
~~~

卷号支持1—9。原有各卷构建脚本保留独立实现，避免一次迁移改变已核验版式。第六卷从清空旧缓存的环境重建，验证记录见 reports/pre-git。

新PDF通过自动检查及视觉复查后，再替换 output/pdf 中的正式版本，并同步进度、当前校核记录和文件哈希。阅读链接指向本地成品；仅克隆Git仓库时该目录为空，可从成品备份恢复，或完成重建及核验后放入。

scripts/convert_volumeN.py 是原始导入流程的参考实现，会拒绝重置已有翻译进度。新增书籍须先适配章节边界、字体、脚注和版面，不能对现有九卷直接重跑初始化。

## 归档与Git范围

清理前完整归档保留在 E:/codes/cambridge-archive-20261101 目录，与 translations 仓库同级，不随本书系目录移动。其 project-before-git.zip 含清理前全部12,206个文件，每个文件均已核对SHA256；包括旧译稿、修订分块、一次性脚本、检查图片和原有备份。归档不进入本仓库，须与仓库分别妥善保存。

归档身份、迁移清单和路径对应表见[入库整理记录](<reports/pre-git/README.md>)。首次提交只记录整理后的基线；首次提交以前的历史由完整归档保留。

源PDF和各卷图像进入Git；成品PDF及tmp缓存不进入Git。后续翻译操作遵循仓库根目录的[AGENTS.md](<../../AGENTS.md>)。

目录调整的对应关系见[目录迁移记录](<reports/directory-layout.json>)。历史报告中的旧项目路径保留为当时的记录；当前脚本以所在书系目录定位输入与输出。
