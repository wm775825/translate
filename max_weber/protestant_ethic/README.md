# 新教伦理与资本主义精神

作者：马克斯·韦伯。本书从[既有翻译仓库](https://github.com/wm775825/translate)迁入，对应原提交139c435。本次整理目录、适配工具路径并检查文件完整性，原译文保持不变。

## 阅读与维护源

- [中文终校稿](<新教伦理与资本主义精神_中文终校稿.md>)：当前阅读及人工修订的唯一维护源。
- [德文原文](<新教伦理与资本主义精神_德文原文.md>)、[原始PDF](<新教伦理与资本主义精神.pdf>)。
- [翻译术语表](<翻译术语表.md>)、[原二校润色规则](<二校润色规则.md>)。

德文Markdown和中文终校稿均保留Seite 1—96的页标题。“中文终校稿”为原文件名，本次不重新评定校订深度。远端没有中文PDF，本次未新增排版成品。

本书沿用整本Markdown维护方式。下列分块和历史合订稿用于回溯；它们不包含终校稿的全部后续整理，不能用其重建结果覆盖终校稿。

## 目录

| 位置 | 内容 |
|---|---|
| 本目录PDF、德文原文、中文终校稿 | 原书及当前阅读文件 |
| data/translated_chunks | 4份初译分块 |
| data/revision_chunks | 16份第一轮二校分块 |
| data/revision_chunks_v2 | 16份第二轮二校分块 |
| data/history | 中文初译合订稿、二校v1和v2合订稿 |
| data/source_pages | 旧项目保留的7份原文页片段 |
| scripts | 合订和问题筛查工具，已适配新目录 |
| reports | 原有两轮问题清单及导入记录 |
| tmp | 重新合订、筛查得到的临时文件，不入Git |

原有问题清单分别针对历史二校v1、v2稿，不能据其“问题候选为0”认定终校稿已通过全面校核。

## 工具使用

从本书目录运行；从仓库根目录开始时，先执行 cd max_weber/protestant_ethic。五个旧工具仅使用Python标准库。

~~~powershell
# 按原有分块重建历史合订稿，输出到tmp/collections
python -X utf8 scripts/merge_translation.py
python -X utf8 scripts/merge_revision.py
python -X utf8 scripts/merge_revision_v2.py

# 对保留的历史二校稿筛查，输出到tmp/reports
python -X utf8 scripts/generate_issue_list.py
python -X utf8 scripts/generate_issue_list_v2.py
~~~

这些命令不修改终校稿、历史底稿或原有报告。脚本继续保留原筛查算法；合订和自动筛查不等于重新翻译或完成语义复核。

## 来源与记录

[导入清单](<reports/import/manifest.json>)逐项记录原路径、新路径和文件哈希；[翻译进度](<翻译进度.json>)记录当前维护源和此次检查范围。原仓库的Git历史保留在合并记录中。清单记载的项目外原始克隆备份位置，在本次整理时未找到；保留历史路径，不将其视为当前可用备份。后续阶段成果和历史版本通过Git提交保存，临时文件放在本书目录内的tmp；默认不再另建备份或打包快照。

工作流遵循仓库根目录的[AGENTS.md](<../../AGENTS.md>)。返回[韦伯书目](<../README.md>)。
