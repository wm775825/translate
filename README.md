# translations

外文书籍翻译项目，按系列或作者，再按主题或书名，保存原书、Markdown译稿、配套资料与维护工具。

## 书籍目录

| 系列／作者 | 主题／书籍 | 内容 |
|---|---|---|
| [剑桥历史系列](<cambridge_history/README.md>) | [基督教史](<cambridge_history/christianity/README.md>) | 九卷中文PDF、原书和中文校订稿 |
| [马克斯·韦伯](<max_weber/README.md>) | [新教伦理与资本主义精神](<max_weber/protestant_ethic/README.md>) | 德文原书、既有中文终校稿、历次底稿及工具 |
| [托马斯·索维尔](<thomas_sowell/README.md>) | [知识与决策](<thomas_sowell/knowledge_and_decisions/README.md>) | 原书、完整中文校订稿及376页中文PDF |

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
├── max_weber/
│   └── protestant_ethic/
│       ├── 新教伦理与资本主义精神.pdf
│       ├── 新教伦理与资本主义精神_德文原文.md
│       ├── 新教伦理与资本主义精神_中文终校稿.md
│       ├── data/
│       ├── scripts/
│       └── reports/
└── thomas_sowell/
    └── knowledge_and_decisions/
        ├── 知识与决策.pdf
        ├── 知识与决策（英文全文）.md
        ├── 知识与决策（中文校订版）.md
        ├── chapters/
        ├── data/
        ├── scripts/
        ├── reports/
        └── output/pdf/
~~~

翻译与校订遵循[工作流规范](<AGENTS.md>)。各套书的工具从对应书系或书籍目录运行，具体操作及维护源见各自README。

原书、译稿、图像、必要构建数据及正式中文PDF进入Git，阶段成果和历史版本通过Git提交保存。各书output/pdf中的正式PDF随仓库发布。翻译过程文件全部保存在对应书籍目录内，临时分块、渲染图和排版中间文件放在tmp，不进入Git。默认不再复制原书、逐轮打包或另存正式PDF备份，也不另建项目外的工作目录。
