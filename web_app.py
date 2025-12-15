#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Charlie Munger's Second Brain - Web 界面
基于 Flask 的现代化 Web UI
"""

import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 全局变量
graph = None
query_engine = None
llm = None
vector_store = None  # 向量存储


def init_app():
    """初始化应用"""
    global graph, query_engine, llm
    
    from src.config import settings
    from src.llm_providers import get_llm
    from src.graph_builder import KnowledgeGraph
    from src.query_engine import GraphQueryEngine
    
    # 检查是否有现有图谱
    output_dir = Path("output/demo")
    if output_dir.exists() and (output_dir / "entities.json").exists():
        graph = KnowledgeGraph()
        graph.load(output_dir)
        llm = get_llm(settings)
        query_engine = GraphQueryEngine(graph, llm)
        print("✅ 已加载现有图谱")
    else:
        print("⚠️ 未找到图谱，请先运行 demo 或 build 命令")


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/stats')
def get_stats():
    """获取图谱统计信息"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    stats = graph.get_stats()
    return jsonify(stats)


@app.route('/api/entities')
def get_entities():
    """获取所有实体"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    entities = []
    for name, entity in graph.entities.items():
        entities.append({
            "name": entity.name,
            "type": entity.entity_type.value,
            "description": entity.description,
            "chapter": entity.source_chapter
        })
    
    return jsonify(entities)


@app.route('/api/relationships')
def get_relationships():
    """获取所有关系"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    relationships = []
    for rel in graph.relationships:
        relationships.append({
            "source": rel.source,
            "target": rel.target,
            "type": rel.relation_type.value,
            "description": rel.description
        })
    
    return jsonify(relationships)


@app.route('/api/graph')
def get_graph_data():
    """获取图谱数据（用于可视化）"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    # 实体类型对应的颜色
    type_colors = {
        "概念": "#e94560",
        "思维模型": "#ff6b6b",
        "原则": "#4ecdc4",
        "人物": "#45b7d1",
        "公司": "#f9ca24",
        "案例": "#6c5ce7",
        "书籍": "#a29bfe",
        "学科": "#00b894",
        "认知偏误": "#fd79a8",
    }
    
    nodes = []
    for name, entity in graph.entities.items():
        entity_type = entity.entity_type.value
        nodes.append({
            "id": name,
            "label": name,
            "type": entity_type,
            "description": entity.description,
            "color": type_colors.get(entity_type, "#95a5a6"),
            "size": 30 if entity_type in ["概念", "思维模型"] else 20
        })
    
    edges = []
    for rel in graph.relationships:
        edges.append({
            "source": rel.source,
            "target": rel.target,
            "label": rel.relation_type.value,
            "description": rel.description
        })
    
    return jsonify({
        "nodes": nodes,
        "edges": edges
    })


@app.route('/api/entity/<name>')
def get_entity(name):
    """获取单个实体详情"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    if name not in graph.entities:
        return jsonify({"error": "实体不存在"}), 404
    
    entity = graph.entities[name]
    neighbors = graph.get_neighbors(name)
    
    return jsonify({
        "name": entity.name,
        "type": entity.entity_type.value,
        "description": entity.description,
        "chapter": entity.source_chapter,
        "neighbors": neighbors
    })


@app.route('/api/query', methods=['POST'])
def query():
    """问答接口"""
    if query_engine is None:
        return jsonify({"error": "查询引擎未初始化"}), 404
    
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({"error": "请输入问题"}), 400
    
    try:
        answer = query_engine.query(question)
        return jsonify({
            "question": question,
            "answer": answer
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/explore/<entity_name>')
def explore(entity_name):
    """探索实体关系"""
    if graph is None:
        return jsonify({"error": "图谱未加载"}), 404
    
    # 模糊匹配
    matched = None
    for name in graph.entities.keys():
        if entity_name.lower() in name.lower() or name.lower() in entity_name.lower():
            matched = name
            break
    
    if not matched:
        return jsonify({"error": f"未找到实体: {entity_name}"}), 404
    
    entity = graph.entities[matched]
    neighbors = graph.get_neighbors(matched)
    
    # 构建子图
    subgraph_nodes = [{"id": matched, "label": matched, "type": entity.entity_type.value, "isCenter": True}]
    subgraph_edges = []
    
    for rel in neighbors.get("in", []):
        if rel["entity"] in graph.entities:
            subgraph_nodes.append({
                "id": rel["entity"],
                "label": rel["entity"],
                "type": graph.entities[rel["entity"]].entity_type.value
            })
            subgraph_edges.append({
                "source": rel["entity"],
                "target": matched,
                "label": rel["relation"]
            })
    
    for rel in neighbors.get("out", []):
        if rel["entity"] in graph.entities:
            subgraph_nodes.append({
                "id": rel["entity"],
                "label": rel["entity"],
                "type": graph.entities[rel["entity"]].entity_type.value
            })
            subgraph_edges.append({
                "source": matched,
                "target": rel["entity"],
                "label": rel["relation"]
            })
    
    return jsonify({
        "center": matched,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges
    })


@app.route('/api/build_from_book', methods=['POST'])
def build_from_book():
    """从书籍中提取知识构建图谱（使用词典匹配）"""
    global graph, query_engine
    
    from src.graph_builder import KnowledgeGraph
    from src.book_extractor import BookKnowledgeExtractor
    from src.visualizer import visualize_graph
    
    book_path = Path("data/processed/穷查理宝典.txt")
    
    if not book_path.exists():
        return jsonify({"error": "书籍文本未提取，请先运行文本提取"}), 400
    
    try:
        # 创建图谱
        graph = KnowledgeGraph()
        
        # 从书中提取知识
        extractor = BookKnowledgeExtractor()
        entities, relationships = extractor.extract_from_file(str(book_path))
        
        # 添加到图谱
        for entity in entities.values():
            graph.add_entity(entity)
        
        for rel in relationships:
            graph.add_relationship(rel)
        
        # 保存
        output_dir = Path("output/book")
        graph.save(output_dir)
        visualize_graph(graph, str(output_dir / "graph.html"))
        
        # 初始化查询引擎
        query_engine = SimpleQueryEngine(graph)
        
        stats = graph.get_stats()
        
        return jsonify({
            "success": True,
            "message": "从《穷查理宝典》提取知识完成！（词典匹配模式）",
            "stats": stats,
            "source": "book_dict"
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/build_with_llm', methods=['POST'])
def build_with_llm():
    """使用 LLM 从书籍中智能提取知识"""
    global graph, query_engine
    
    from src.config import settings
    from src.llm_providers import get_llm
    from src.graph_builder import KnowledgeGraph
    from src.llm_extractor import LLMKnowledgeExtractor
    from src.visualizer import visualize_graph
    
    book_path = Path("data/processed/穷查理宝典.txt")
    
    if not book_path.exists():
        return jsonify({"error": "书籍文本未提取"}), 400
    
    try:
        # 初始化 LLM
        llm = get_llm(settings)
        
        # 创建图谱
        graph = KnowledgeGraph()
        
        # 使用 LLM 提取知识（优化成本：增大块大小，减少调用次数）
        extractor = LLMKnowledgeExtractor(llm, chunk_size=4000)
        entities, relationships = extractor.extract_from_file(str(book_path), max_chunks=10)
        
        # 添加到图谱
        for entity in entities.values():
            graph.add_entity(entity)
        
        for rel in relationships:
            graph.add_relationship(rel)
        
        # 保存
        output_dir = Path("output/llm")
        graph.save(output_dir)
        visualize_graph(graph, str(output_dir / "graph.html"))
        
        # 初始化查询引擎
        query_engine = SimpleQueryEngine(graph)
        
        stats = graph.get_stats()
        
        return jsonify({
            "success": True,
            "message": "使用 LLM 智能提取完成！",
            "stats": stats,
            "source": "llm"
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/build_vector_index', methods=['POST'])
def build_vector_index():
    """构建向量索引（用于语义搜索）"""
    global vector_store
    
    from src.vector_store import VectorStore
    
    book_path = Path("data/processed/穷查理宝典.txt")
    
    if not book_path.exists():
        return jsonify({"error": "书籍文本未提取"}), 400
    
    try:
        # 创建向量存储（使用通义千问 Embedding）
        vector_store = VectorStore(embedding_model="dashscope")
        
        # 构建索引
        vector_store.build_from_file(str(book_path), chunk_size=500, chunk_overlap=100)
        
        # 保存索引
        output_dir = Path("output/vector")
        vector_store.save(str(output_dir))
        
        return jsonify({
            "success": True,
            "message": "向量索引构建完成！",
            "chunks": len(vector_store.chunks),
            "dimension": vector_store.dimension
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/search', methods=['POST'])
def vector_search():
    """向量语义搜索"""
    global vector_store
    
    if vector_store is None:
        # 尝试加载已有索引
        from src.vector_store import VectorStore
        vector_store = VectorStore(embedding_model="dashscope")
        if not vector_store.load("output/vector"):
            return jsonify({"error": "向量索引未构建，请先构建索引"}), 400
    
    data = request.get_json()
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    
    if not query:
        return jsonify({"error": "请输入搜索内容"}), 400
    
    try:
        results = vector_store.search(query, top_k=top_k)
        
        return jsonify({
            "query": query,
            "results": [
                {
                    "text": chunk.text,
                    "chapter": chunk.chapter,
                    "score": float(score)
                }
                for chunk, score in results
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hybrid_query', methods=['POST'])
def hybrid_query():
    """混合查询：向量检索 + 图谱 + LLM（支持多轮对话）"""
    global vector_store, graph, llm
    
    from src.config import settings
    from src.llm_providers import get_llm
    from src.vector_store import VectorStore, HybridQueryEngine
    
    # 确保有向量索引
    if vector_store is None:
        vector_store = VectorStore(embedding_model="dashscope")
        if not vector_store.load("output/vector"):
            return jsonify({"error": "向量索引未构建"}), 400
    
    # 确保有 LLM
    if llm is None:
        llm = get_llm(settings)
    
    data = request.get_json()
    question = data.get('question', '')
    history = data.get('history', [])  # 对话历史 [{role: 'user'/'assistant', content: '...'}]
    
    if not question:
        return jsonify({"error": "请输入问题"}), 400
    
    try:
        # 创建混合查询引擎
        engine = HybridQueryEngine(vector_store, graph, llm)
        result = engine.query(question, top_k=5, history=history)
        
        return jsonify({
            "question": question,
            "answer": result["answer"],
            "citations": result["citations"],
            "graph_entities": result["graph_entities"],
            "mode": "hybrid"
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route('/api/build_demo', methods=['POST'])
def build_demo():
    """构建演示图谱（使用预定义数据，无需 LLM）"""
    global graph, query_engine, llm
    
    from src.graph_builder import KnowledgeGraph
    from src.schema import Entity, Relationship, EntityType, RelationType
    from src.visualizer import visualize_graph
    
    try:
        # 创建知识图谱
        graph = KnowledgeGraph()
        
        # 添加核心概念
        graph.add_core_concepts()
        
        # 添加演示实体
        demo_entities = [
            Entity("激励机制", EntityType.MENTAL_MODEL, "改变激励比说教更有效"),
            Entity("铁锤人综合征", EntityType.COGNITIVE_BIAS, "手里拿着锤子的人，看什么都像钉子"),
            Entity("复利思维", EntityType.MENTAL_MODEL, "指数级增长的力量"),
            Entity("社会认同", EntityType.COGNITIVE_BIAS, "从众心理，做周围人正在做的事"),
            Entity("联邦快递案例", EntityType.CASE_STUDY, "将计时工资改成计件工资解决效率问题"),
            Entity("互联网泡沫", EntityType.CASE_STUDY, "1999年科技股泡沫"),
            Entity("查理·芒格", EntityType.PERSON, "伯克希尔·哈撒韦副董事长，多元思维模型倡导者"),
            Entity("沃伦·巴菲特", EntityType.PERSON, "伯克希尔·哈撒韦CEO，价值投资大师"),
            Entity("本杰明·富兰克林", EntityType.PERSON, "美国开国元勋，复利思想的传播者"),
            Entity("伯克希尔·哈撒韦", EntityType.COMPANY, "芒格和巴菲特的投资公司"),
            Entity("心理学", EntityType.DISCIPLINE, "研究人类心理和行为的学科"),
            Entity("经济学", EntityType.DISCIPLINE, "研究资源配置的学科"),
            Entity("物理学", EntityType.DISCIPLINE, "研究物质规律的学科"),
        ]
        
        for entity in demo_entities:
            graph.add_entity(entity)
        
        # 添加关系
        demo_relationships = [
            Relationship("激励机制", "联邦快递案例", RelationType.EXPLAINS, "激励机制解释了联邦快递的成功"),
            Relationship("查理·芒格", "多元思维模型", RelationType.SUPPORTS, "芒格是多元思维模型的倡导者"),
            Relationship("查理·芒格", "沃伦·巴菲特", RelationType.COLLABORATED_WITH, "芒格与巴菲特是长期合作伙伴"),
            Relationship("复利思维", "本杰明·富兰克林", RelationType.DERIVED_FROM, "复利思维源自富兰克林"),
            Relationship("复利思维", "伯克希尔·哈撒韦", RelationType.APPLIES_TO, "复利思维应用于伯克希尔"),
            Relationship("社会认同", "互联网泡沫", RelationType.LEADS_TO, "社会认同导致了互联网泡沫"),
            Relationship("铁锤人综合征", "多元思维模型", RelationType.OPPOSES, "铁锤人综合征与多元思维相悖"),
            Relationship("激励机制", "心理学", RelationType.DERIVED_FROM, "激励机制源自心理学"),
            Relationship("多元思维模型", "心理学", RelationType.PART_OF, "心理学是多元思维的一部分"),
            Relationship("多元思维模型", "经济学", RelationType.PART_OF, "经济学是多元思维的一部分"),
            Relationship("多元思维模型", "物理学", RelationType.PART_OF, "物理学是多元思维的一部分"),
            Relationship("逆向思考", "多元思维模型", RelationType.PART_OF, "逆向思考是多元思维的核心"),
            Relationship("能力圈", "安全边际", RelationType.RELATED_TO, "能力圈与安全边际相辅相成"),
            Relationship("查理·芒格", "逆向思考", RelationType.SUPPORTS, "芒格名言：反过来想，总是反过来想"),
            Relationship("社会认同倾向", "社会认同", RelationType.IS_A, "社会认同倾向是一种认知偏误"),
        ]
        
        for rel in demo_relationships:
            graph.add_relationship(rel)
        
        # 保存
        output_dir = Path("output/demo")
        graph.save(output_dir)
        visualize_graph(graph, str(output_dir / "graph.html"))
        
        # 初始化简单的查询引擎
        query_engine = SimpleQueryEngine(graph)
        
        stats = graph.get_stats()
        
        return jsonify({
            "success": True,
            "message": "演示图谱构建完成！",
            "stats": stats
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


class SimpleQueryEngine:
    """简单的查询引擎（不依赖 LLM）"""
    
    def __init__(self, graph):
        self.graph = graph
        
        # 预定义问答库（更丰富的回答）
        self.qa_library = {
            "逆向": (
                "## 🔄 逆向思维（Inversion）\n\n"
                "**芒格的名言**：'反过来想，总是反过来想。'（Invert, always invert.）\n\n"
                "### 核心思想\n"
                "逆向思维是芒格最推崇的思维方法之一。它源自数学家卡尔·雅可比的名言。\n\n"
                "### 应用方法\n"
                "- 想知道**如何成功**？先研究**什么会导致失败**\n"
                "- 想知道**如何幸福**？先研究**什么会导致不幸**\n"
                "- 想知道**如何投资成功**？先研究**如何避免亏损**\n\n"
                "### 实际案例\n"
                "芒格在分析投资时，会先列出所有可能失败的原因，然后逐一避免。\n"
                "这比直接追求成功更有效，因为**避免愚蠢比追求聪明更容易**。\n\n"
                "### 与其他思维模型的关系\n"
                "- 逆向思维是**多元思维模型**的核心组成部分\n"
                "- 它与**检查清单**方法相辅相成"
            ),
            "激励": (
                "## 💰 激励机制\n\n"
                "**芒格的名言**：'永远不要低估激励机制的力量。'\n\n"
                "### 核心思想\n"
                "如果你想改变某人的行为，改变激励机制比说教更有效。\n\n"
                "### 经典案例：联邦快递\n"
                "联邦快递曾遇到夜班工人效率低下的问题。管理层尝试了各种方法都无效，"
                "直到把**计时工资改成计件工资**，问题立刻解决了。\n\n"
                "### 投资启示\n"
                "在分析公司时，要关注管理层的激励机制是否与股东利益一致。"
            ),
            "铁锤": (
                "## 🔨 铁锤人综合征\n\n"
                "**芒格的名言**：'手里拿着锤子的人，看什么都像钉子。'\n\n"
                "### 问题表现\n"
                "- 经济学家倾向于用经济学解释一切\n"
                "- 心理学家用心理学解释一切\n"
                "- 每个专业人士都倾向于用自己熟悉的工具\n\n"
                "### 解决方案\n"
                "采用**多元思维模型**，从多个学科借鉴思维工具，避免单一视角的局限。"
            ),
            "复利": (
                "## 📈 复利思维\n\n"
                "本杰明·富兰克林曾说复利是'世界第八大奇迹'。\n\n"
                "### 芒格的理解\n"
                "复利的力量不仅在投资中有效，在**知识积累**、**声誉建设**等方面也是如此。\n\n"
                "### 伯克希尔的实践\n"
                "巴菲特和芒格坚持不分红，让资金在公司内部持续复利增长。"
                "这是伯克希尔成功的关键因素之一。"
            ),
            "多元思维": (
                "## 🧠 多元思维模型\n\n"
                "这是芒格思想的**核心框架**。\n\n"
                "### 核心理念\n"
                "要理解复杂世界，需要融合多个学科的思维工具，形成一个'思维模型格栅'。\n\n"
                "### 包含的学科\n"
                "- 📐 数学：复利、概率论\n"
                "- 🔬 物理学：临界点、均衡\n"
                "- 🧬 生物学：进化论、生态位\n"
                "- 🧠 心理学：认知偏误\n"
                "- 💰 经济学：激励机制、机会成本"
            ),
            "能力圈": (
                "## ⭕ 能力圈\n\n"
                "### 核心含义\n"
                "只在自己**真正理解**的领域投资。\n\n"
                "### 芒格的观点\n"
                "关键不在于能力圈有多大，而在于**知道边界在哪里**。\n\n"
                "### 实践\n"
                "芒格和巴菲特因此错过了很多科技股，但也避免了更多的失败投资。"
            ),
            "社会认同": (
                "## 👥 社会认同倾向\n\n"
                "这是芒格总结的25种认知偏误之一，也叫**从众心理**。\n\n"
                "### 表现\n"
                "人们倾向于做周围人正在做的事情。\n\n"
                "### 投资中的危险\n"
                "1999年互联网泡沫时期，几乎所有人都在追捧科技股，"
                "芒格和巴菲特却选择袖手旁观。\n\n"
                "**在市场疯狂时保持理性是最困难也是最重要的事情。**"
            ),
        }
    
    def query(self, question):
        """基于关键词匹配的智能问答"""
        question_lower = question.lower()
        
        # 1. 首先检查预定义问答库（最精准）
        for keyword, answer in self.qa_library.items():
            if keyword in question_lower or keyword in question:
                # 找到匹配，补充图谱中的关系信息
                related_info = self._get_related_from_graph(keyword)
                if related_info:
                    return answer + "\n\n---\n\n### 📊 知识图谱中的关联\n" + related_info
                return answer
        
        # 2. 精确匹配实体名称
        for name, entity in self.graph.entities.items():
            if name in question or question.replace("什么是", "").replace("？", "").strip() == name:
                return self._format_entity_answer(entity)
        
        # 3. 模糊匹配
        matches = []
        for name, entity in self.graph.entities.items():
            # 计算匹配得分
            score = 0
            for char in question:
                if char in name and char not in "？?的是什么怎么如何为介绍一下":
                    score += 1
            if score >= 2:  # 至少匹配2个字符
                matches.append((entity, score))
        
        if matches:
            # 按得分排序，取最相关的
            matches.sort(key=lambda x: -x[1])
            best_entity = matches[0][0]
            return self._format_entity_answer(best_entity)
        
        return (
            "抱歉，我没有找到与您问题直接相关的信息。\n\n"
            "💡 **您可以尝试问：**\n"
            "- 什么是逆向思维？\n"
            "- 介绍一下多元思维模型\n"
            "- 什么是激励机制？\n"
            "- 什么是能力圈？\n"
            "- 什么是复利思维？"
        )
    
    def _format_entity_answer(self, entity):
        """格式化单个实体的详细回答"""
        lines = []
        
        # 标题
        type_emoji = {
            "概念": "💡", "思维模型": "🧠", "原则": "📐",
            "人物": "👤", "公司": "🏢", "案例": "📋",
            "学科": "📚", "认知偏误": "⚠️", "书籍": "📖"
        }
        emoji = type_emoji.get(entity.entity_type.value, "📌")
        lines.append(f"## {emoji} {entity.name}\n")
        lines.append(f"**类型**：{entity.entity_type.value}\n")
        
        # 描述
        if entity.description:
            lines.append(f"**描述**：{entity.description}\n")
        
        # 关系
        neighbors = self.graph.get_neighbors(entity.name)
        
        if neighbors.get("out") or neighbors.get("in"):
            lines.append("\n### 🔗 相关联的概念\n")
            
            if neighbors.get("out"):
                for rel in neighbors["out"][:5]:
                    lines.append(f"- → **{rel['relation']}** → {rel['entity']}")
            
            if neighbors.get("in"):
                for rel in neighbors["in"][:5]:
                    lines.append(f"- ← **{rel['relation']}** ← {rel['entity']}")
        
        return "\n".join(lines)
    
    def _get_related_from_graph(self, keyword):
        """从图谱中获取相关信息"""
        related = []
        for name, entity in self.graph.entities.items():
            if keyword in name.lower():
                neighbors = self.graph.get_neighbors(name)
                if neighbors.get("out"):
                    for rel in neighbors["out"][:2]:
                        related.append(f"- {name} → **{rel['relation']}** → {rel['entity']}")
                if neighbors.get("in"):
                    for rel in neighbors["in"][:2]:
                        related.append(f"- {rel['entity']} → **{rel['relation']}** → {name}")
        return "\n".join(related[:5]) if related else ""


if __name__ == '__main__':
    import os
    
    # 支持自定义端口，默认 6006（AutoDL 常用端口）
    port = int(os.environ.get('PORT', 6006))
    
    print("\n" + "="*60)
    print("🧠 Charlie Munger's Second Brain - Web UI")
    print("="*60)
    
    init_app()
    
    print("\n🌐 启动 Web 服务器...")
    print(f"📍 本地访问: http://localhost:{port}")
    print("📍 AutoDL 用户：请在控制台开启「自定义服务」端口映射")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

