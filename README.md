# translations

外文书籍翻译项目，按系列或作者，再按主题或书名，保存原书、Markdown译稿、配套资料与维护工具。

## 书籍目录

| 系列／作者 | 主题／书籍 | 内容 |
|---|---|---|
| [剑桥历史系列](<cambridge_history/README.md>) | [基督教史](<cambridge_history/christianity/README.md>) | 九卷原书、中文校订稿及本地PDF |
| [马克斯·韦伯](<max_weber/README.md>) | [新教伦理与资本主义精神](<max_weber/protestant_ethic/README.md>) | 德文原书、既有中文终校稿、历次底稿及工具 |

~~~text
translations/
├── AGENTS.md
├── cambridge_history/
│   └── christianity/
│       ├── 01 起源至君士坦丁.pdf … 09 世界基督教（1914-2000）.pdf
│       ├── 第一卷/ … 第九卷/
│       ├── data/
│       ├── scripts/
│       ├── reports/
│       └── output/pdf/
└── max_weber/
    └── protestant_ethic/
        ├── 新教伦理与资本主义精神.pdf
        ├── 新教伦理与资本主义精神_德文原文.md
        ├── 新教伦理与资本主义精神_中文终校稿.md
        ├── data/
        ├── scripts/
        └── reports/
~~~

翻译与校订遵循[工作流规范](<AGENTS.md>)。各套书的工具从对应书系或书籍目录运行，具体操作及维护源见各自README。

原书、译稿、图像及必要构建数据进入Git；各层目录中的output成品和tmp缓存不进入Git，正式PDF另行备份。现有清理前归档仍保存在仓库外的 E:/codes/cambridge-archive-20261101。
