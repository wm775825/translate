# 首次入库整理

整理日期：2026-11-01。

完整归档位于项目相邻目录 cambridge-archive-20261101 的 project-before-git.zip，包含清理前全部12,206个文件，逐文件SHA256已验证。归档文件的SHA256见 archive.json。

本目录保留：

- source-files.json：完整归档的原始文件清单、大小和哈希。
- protected-content.json：必须原样保留的原书、译稿、图像和正式成品内容基线。
- path-map.json：被迁出tmp的脚本、数据和检查记录的新路径。
- migration.json：迁移范围及删除的九份重复Markdown。
- 后续验证结果：输入与本地链接检查、九卷合订稿对照、第六卷从空缓存重建的文字、注释、链接、分页及视觉验证。

历史文件若未保留在仓库中，可按source-files.json中的相对路径从完整ZIP归档恢复。完整归档及本地output/pdf成品需要另外备份，Git不会自动保存首次提交之前的历史。
