# 🧠 Charlie Munger's Second Brain

> **穷查理宝典 GraphRAG 知识图谱系统**

基于 GraphRAG 技术，将《穷查理宝典》中芒格的多元思维模型转化为可交互的知识图谱，实现跨章节归纳、隐性关系发现等高级问答能力。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/LlamaIndex-0.10+-green.svg" alt="LlamaIndex">
  <img src="https://img.shields.io/badge/NetworkX-3.0+-orange.svg" alt="NetworkX">
</p>

---

## ✨ 为什么要做这个项目？

传统的向量检索（Vector RAG）对《穷查理宝典》效果不好，因为芒格的思想是**网状**的：

| 场景 | Vector RAG 痛点 | GraphRAG 优势 |
|------|-----------------|---------------|
| 搜索"复利" | 返回10个相似片段，看不出所以然 | 聚合所有论述，生成全局总结 |
| 搜索"物理学与投资" | 向量距离远，检索不到 | 通过关系路径找到深层联系 |
| 问"芒格的所有思维模型" | 只能返回部分片段 | 遍历图谱，完整归纳 |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API

复制并编辑配置文件：

```bash
cp env.example .env
```

编辑 `.env` 文件，填入你的 API Key（支持多种 LLM）：

```bash
# 推荐使用通义千问（中文效果好，价格便宜）
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEYS=sk-your-key-here
```

### 3. 运行演示

```bash
python main.py demo
```

这会使用内置的示例文本构建一个小型图谱，并演示问答功能。

### 4. 处理完整书籍

将《穷查理宝典》文本放入 `data/raw/` 目录，然后：

```bash
python main.py build data/raw/穷查理宝典.txt
```

### 5. 交互式问答

```bash
python main.py query
```

---

## 📊 图谱设计

专为《穷查理宝典》定制的实体和关系类型：

### 实体类型 (Entities)

| 类型 | 说明 | 示例 |
|------|------|------|
| 概念 | 思维框架、原则 | 多元思维模型、能力圈 |
| 思维模型 | 具体的思维工具 | 逆向思考、费马-帕斯卡系统 |
| 人物 | 书中提到的人 | 本杰明·富兰克林、巴菲特 |
| 案例 | 投资/商业案例 | 喜诗糖果收购、联邦快递 |
| 认知偏误 | 25种误判心理学 | 铁锤人综合征、社会认同 |
| 学科 | 涉及的学科 | 物理学、心理学、经济学 |

### 关系类型 (Relationships)

| 关系 | 说明 | 示例 |
|------|------|------|
| 解释 | 模型解释现象 | 激励机制 --解释--> 联邦快递案例 |
| 源自 | 思维来源 | 复利思维 --源自--> 本杰明·富兰克林 |
| 应用于 | 原则应用 | 安全边际 --应用于--> 投资决策 |
| 反对 | 反对观点 | 芒格 --反对--> 有效市场假说 |
| 导致 | 因果关系 | 社会认同 --导致--> 市场泡沫 |

---

## 🔧 支持的 LLM

| 提供商 | 配置项 | 推荐模型 | 特点 |
|--------|--------|----------|------|
| 通义千问 | `dashscope` | qwen-plus | 中文最佳，性价比高 |
| 智谱 AI | `zhipuai` | glm-4-flash | 响应快 |
| 302.AI | `openai` | gpt-4o-mini | 支持多种模型 |
| 火山方舟 | `ark` | doubao-pro | 豆包模型 |

---

## 📁 项目结构

```
charlie-munger-brain/
├── data/
│   ├── raw/              # 原始文本（放入书籍）
│   └── processed/        # 处理后的数据
├── output/               # 输出目录
│   ├── knowledge_graph.graphml  # 图谱文件
│   ├── graph.html        # 交互式可视化
│   └── report.md         # 自动生成的报告
├── src/
│   ├── config.py         # 配置管理
│   ├── llm_providers.py  # 多 LLM 支持
│   ├── schema.py         # 实体/关系定义
│   ├── graph_builder.py  # 图谱构建
│   ├── query_engine.py   # 查询引擎
│   └── visualizer.py     # 可视化
├── main.py               # 主入口
├── requirements.txt      # 依赖
└── README.md
```

---

## 💡 使用示例

### 能回答的高级问题

这个系统能回答**普通 RAG 答不出来的**问题：

**Q1: 跨章节归纳**
> "芒格提到的所有'跨学科思维模型'里，哪些是来自硬科学（物理/数学）的？"

**Q2: 隐性关系**  
> "富兰克林的思想是如何具体影响芒格的投资决策的？"
>
> GraphRAG 能找到路径：`富兰克林 → 诚实/正直 → 伯克希尔的信誉 → 低成本浮存金`

**Q3: 反向探索**
> "哪些认知偏误可能导致投资失败？"

### 命令行用法

```bash
# 运行演示
python main.py demo

# 从文件构建图谱
python main.py build data/raw/book.txt -o output

# 交互式问答
python main.py query

# 重新生成可视化
python main.py viz output
```

### 交互式探索

在问答模式中，可以使用特殊命令：

```
> explore 复利           # 从"复利"节点开始探索图谱
> show 铁锤人综合征       # 显示实体详情和关系
> quit                   # 退出
```

---

## 🎯 技术架构

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Raw Text   │ ──▶ │  Chunking    │ ──▶ │  LLM        │
│  (PDF/TXT)  │     │  (按章节分块)  │     │ (实体提取)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Answer     │ ◀── │  Query       │ ◀── │  Knowledge  │
│  Generation │     │  Engine      │     │  Graph      │
└─────────────┘     └──────────────┘     └─────────────┘
```

---

## 📈 后续计划

- [ ] 支持 Neo4j 图数据库
- [ ] 添加社区检测算法
- [ ] 支持增量更新图谱
- [ ] Web UI 界面
- [ ] 多书籍支持

---

## 📖 参考资料

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [LlamaIndex PropertyGraph](https://docs.llamaindex.ai/en/stable/examples/property_graph/)
- 《穷查理宝典》 - 查理·芒格

---

## 📄 License

MIT License

---

> *"反过来想，总是反过来想。" —— 查理·芒格*

