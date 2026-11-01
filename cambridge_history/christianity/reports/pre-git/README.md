# 首次入库整理

整理日期：2026-11-01。

历史记录中的完整归档为E:/codes/cambridge-archive-20261101/project-before-git.zip，记录包含清理前全部12,206个文件及当时的逐文件SHA256核验。2026年11月1日本次整理时，该旧位置未找到归档，未计入迁入文件，也不视为当前可用备份。归档当时的SHA256见archive.json，历史记录保持原样。后续版本通过Git提交保存，默认不再另建备份或打包快照。

本目录保留：

- source-files.json：完整归档的原始文件清单、大小和哈希。
- protected-content.json：必须原样保留的原书、译稿、图像和正式成品内容基线。
- path-map.json：被迁出tmp的脚本、数据和检查记录的新路径。
- migration.json：迁移范围及删除的九份重复Markdown。
- 后续验证结果：输入与本地链接检查、九卷合订稿对照、第六卷从空缓存重建的文字、注释、链接、分页及视觉验证。

历史文件若未保留在仓库中，可按source-files.json中的相对路径从完整ZIP归档恢复。完整归档及本地output/pdf成品需要另外备份，Git不会自动保存首次提交之前的历史。

本目录记录首次入库时的情况；其中原项目绝对路径保持历史原貌。书系内相对路径仍以 cambridge_history/christianity 为根目录，后续目录调整见[目录迁移记录](<../directory-layout.json>)。

后续交付规则已调整：正式中文PDF现已纳入Git并随仓库发布，存放在书系的output/pdf目录。本目录的原始清单保留首次整理时的记录。
