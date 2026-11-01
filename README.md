# translations

外文书籍翻译项目，按系列和主题保存原书、Markdown译稿、配套资料与维护工具。

## 书籍目录

| 系列 | 主题 | 内容 |
|---|---|---|
| [剑桥历史系列](<cambridge_history/README.md>) | [基督教史](<cambridge_history/christianity/README.md>) | 九卷原书、中文校订稿及本地PDF |

~~~text
translations/
├── AGENTS.md
└── cambridge_history/
    └── christianity/
        ├── 01 起源至君士坦丁.pdf … 09 世界基督教（1914-2000）.pdf
        ├── 第一卷/ … 第九卷/
        ├── data/
        ├── scripts/
        ├── reports/
        └── output/pdf/
~~~

翻译与校订遵循[工作流规范](<AGENTS.md>)。各套书的工具从对应书系目录运行；《剑桥基督教史》的操作说明见[书系README](<cambridge_history/christianity/README.md>)。

原书、译稿、图像及必要构建数据进入Git；各层目录中的output成品和tmp缓存不进入Git，正式PDF另行备份。现有清理前归档仍保存在仓库外的 E:/codes/cambridge-archive-20261101。
