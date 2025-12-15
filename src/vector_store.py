"""
向量检索模块
使用 Embedding 实现语义搜索
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.progress import track

console = Console()


@dataclass
class TextChunk:
    """文本块"""
    text: str
    chapter: str
    index: int
    

class VectorStore:
    """向量存储和检索"""
    
    def __init__(self, embedding_model: str = "dashscope"):
        """
        Args:
            embedding_model: 使用的 embedding 模型
                - "dashscope": 使用通义千问 embedding（需要 API Key）
                - "local": 使用本地模型（免费但较慢）
        """
        self.embedding_model = embedding_model
        self.chunks: List[TextChunk] = []
        self.embeddings: Optional[np.ndarray] = None
        self.dimension = 0
        
        # 初始化 embedding 函数
        if embedding_model == "dashscope":
            self._init_dashscope_embedding()
        else:
            self._init_local_embedding()
    
    def _init_dashscope_embedding(self):
        """初始化通义千问 Embedding"""
        try:
            import dashscope
            from dashscope import TextEmbedding
            
            # 从环境变量获取 API Key
            api_key = os.getenv("DASHSCOPE_API_KEYS") or os.getenv("DASHSCOPE_API_KEY")
            if api_key:
                dashscope.api_key = api_key
            
            self.dimension = 1536  # text-embedding-v2 维度
            
            def embed_texts(texts: List[str]) -> np.ndarray:
                """批量生成 embedding"""
                embeddings = []
                # DashScope 每次最多处理 25 个文本
                batch_size = 25
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = TextEmbedding.call(
                        model="text-embedding-v2",
                        input=batch
                    )
                    if response.status_code == 200:
                        for item in response.output['embeddings']:
                            embeddings.append(item['embedding'])
                    else:
                        console.print(f"[yellow]Embedding 失败: {response.message}[/yellow]")
                        # 失败时用零向量填充
                        for _ in batch:
                            embeddings.append([0.0] * self.dimension)
                
                return np.array(embeddings, dtype=np.float32)
            
            self._embed_texts = embed_texts
            console.print("[green]✅ 使用通义千问 Embedding (text-embedding-v2)[/green]")
            
        except Exception as e:
            console.print(f"[yellow]DashScope Embedding 初始化失败: {e}，回退到本地模型[/yellow]")
            self._init_local_embedding()
    
    def _init_local_embedding(self):
        """初始化本地 Embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            console.print("[yellow]正在加载本地 Embedding 模型（首次可能需要下载）...[/yellow]")
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = 384
            
            def embed_texts(texts: List[str]) -> np.ndarray:
                return self.model.encode(texts, show_progress_bar=False)
            
            self._embed_texts = embed_texts
            console.print("[green]✅ 使用本地 Embedding 模型[/green]")
            
        except Exception as e:
            console.print(f"[red]本地模型加载失败: {e}[/red]")
            raise
    
    def build_from_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 100):
        """从文本构建向量索引"""
        console.print("[cyan]📚 构建向量索引...[/cyan]")
        
        # 1. 分块
        self.chunks = self._split_text(text, chunk_size, chunk_overlap)
        console.print(f"  📄 共 {len(self.chunks)} 个文本块")
        
        # 2. 生成 embedding
        console.print(f"  🔄 生成 Embedding（这可能需要一些时间）...")
        texts = [chunk.text for chunk in self.chunks]
        
        # 分批处理避免内存问题
        batch_size = 100
        all_embeddings = []
        
        for i in track(range(0, len(texts), batch_size), description="生成向量"):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._embed_texts(batch)
            all_embeddings.append(batch_embeddings)
        
        self.embeddings = np.vstack(all_embeddings)
        console.print(f"  ✅ 向量索引构建完成！维度: {self.embeddings.shape}")
    
    def build_from_file(self, file_path: str, chunk_size: int = 500, chunk_overlap: int = 100):
        """从文件构建向量索引"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        self.build_from_text(text, chunk_size, chunk_overlap)
    
    def _split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[TextChunk]:
        """将文本分割成块"""
        chunks = []
        
        # 按章节分割
        import re
        sections = re.split(r'\n===\s*(.*?)\s*===\n', text)
        
        current_chapter = "未知章节"
        for i, section in enumerate(sections):
            if i % 2 == 1:
                # 这是章节标题
                current_chapter = section
                continue
            
            section = section.strip()
            if len(section) < 50:
                continue
            
            # 按段落进一步分割
            paragraphs = section.split('\n\n')
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(TextChunk(
                            text=current_chunk.strip(),
                            chapter=current_chapter,
                            index=len(chunks)
                        ))
                    # 保留重叠部分
                    if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                        current_chunk = current_chunk[-chunk_overlap:] + para + "\n\n"
                    else:
                        current_chunk = para + "\n\n"
            
            if current_chunk.strip():
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    chapter=current_chapter,
                    index=len(chunks)
                ))
        
        return chunks
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[TextChunk, float]]:
        """搜索最相关的文本块"""
        if self.embeddings is None or len(self.chunks) == 0:
            return []
        
        # 生成查询向量
        query_embedding = self._embed_texts([query])[0]
        
        # 计算余弦相似度
        # 归一化
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
        embeddings_norm = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-9)
        
        # 计算相似度
        similarities = np.dot(embeddings_norm, query_norm)
        
        # 获取 top_k 结果
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((self.chunks[idx], float(similarities[idx])))
        
        return results
    
    def save(self, output_dir: str):
        """保存向量索引"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 chunks
        chunks_data = [
            {"text": c.text, "chapter": c.chapter, "index": c.index}
            for c in self.chunks
        ]
        with open(output_dir / "chunks.json", 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        # 保存 embeddings
        if self.embeddings is not None:
            np.save(output_dir / "embeddings.npy", self.embeddings)
        
        console.print(f"[green]✅ 向量索引已保存到 {output_dir}[/green]")
    
    def load(self, input_dir: str) -> bool:
        """加载向量索引"""
        input_dir = Path(input_dir)
        
        chunks_path = input_dir / "chunks.json"
        embeddings_path = input_dir / "embeddings.npy"
        
        if not chunks_path.exists() or not embeddings_path.exists():
            return False
        
        # 加载 chunks
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        self.chunks = [
            TextChunk(text=c["text"], chapter=c["chapter"], index=c["index"])
            for c in chunks_data
        ]
        
        # 加载 embeddings
        self.embeddings = np.load(embeddings_path)
        
        console.print(f"[green]✅ 已加载向量索引: {len(self.chunks)} 个文本块[/green]")
        return True


class HybridQueryEngine:
    """混合查询引擎：结合向量检索 + 图谱检索（支持多轮对话）"""
    
    def __init__(self, vector_store: VectorStore, graph, llm):
        self.vector_store = vector_store
        self.graph = graph
        self.llm = llm
    
    def query(self, question: str, top_k: int = 5, history: List[Dict] = None) -> Dict:
        """处理用户问题，返回结构化结果
        
        Args:
            question: 当前问题
            top_k: 检索的文档数量
            history: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
        """
        console.print(f"\n[bold cyan]问题:[/bold cyan] {question}")
        if history:
            console.print(f"[dim]📜 对话历史: {len(history)} 轮[/dim]")
        
        # 1. 向量检索：从书中找到相关段落（也考虑对话上下文）
        console.print("[dim]🔍 从书中检索相关段落...[/dim]")
        # 结合历史问题进行检索
        search_query = self._build_search_query(question, history)
        vector_results = self.vector_store.search(search_query, top_k=top_k)
        
        # 2. 图谱检索：找到相关实体和关系
        console.print("[dim]🔗 从知识图谱检索...[/dim]")
        graph_context = self._get_graph_context(question)
        
        # 3. 组合上下文
        context = self._build_context(vector_results, graph_context)
        
        # 4. 生成回答（传入对话历史）
        answer = self._generate_answer(question, context, vector_results, history)
        
        # 5. 提取引用信息
        citations = self._extract_citations(vector_results)
        
        return {
            "answer": answer,
            "citations": citations,
            "graph_entities": self._get_matched_entities(question)
        }
    
    def _build_search_query(self, question: str, history: List[Dict] = None) -> str:
        """构建搜索查询（结合对话历史）"""
        if not history:
            return question
        
        # 提取最近2轮对话中的关键信息
        recent_context = []
        for msg in history[-4:]:  # 最近2轮（4条消息）
            if msg.get("role") == "user":
                recent_context.append(msg.get("content", "")[:100])
        
        # 组合查询
        if recent_context:
            return f"{' '.join(recent_context)} {question}"
        return question
    
    def _get_matched_entities(self, question: str) -> List[Dict]:
        """获取匹配的实体列表"""
        if self.graph is None:
            return []
        
        matched = []
        for name, entity in self.graph.entities.items():
            if any(char in name for char in question if char not in "？?的是什么怎么如何为"):
                matched.append({
                    "name": name,
                    "type": entity.entity_type.value,
                    "description": entity.description
                })
        return matched[:5]
    
    def _extract_citations(self, vector_results: List[Tuple[TextChunk, float]]) -> List[Dict]:
        """提取引用信息"""
        citations = []
        for i, (chunk, score) in enumerate(vector_results):
            if score > 0.3:
                citations.append({
                    "id": i + 1,
                    "chapter": chunk.chapter,
                    "text": chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
                    "score": round(score, 3)
                })
        return citations
    
    def _get_graph_context(self, question: str) -> str:
        """从图谱获取相关上下文"""
        if self.graph is None:
            return ""
        
        context_parts = []
        
        # 在实体中搜索
        for name, entity in self.graph.entities.items():
            # 简单匹配
            if any(char in name for char in question if char not in "？?的是什么怎么如何为"):
                context_parts.append(f"- **{name}**（{entity.entity_type.value}）：{entity.description}")
                
                # 获取关系
                neighbors = self.graph.get_neighbors(name)
                if neighbors.get("out"):
                    for rel in neighbors["out"][:3]:
                        context_parts.append(f"  → {rel['relation']} → {rel['entity']}")
        
        return "\n".join(context_parts[:10])
    
    def _build_context(self, vector_results: List[Tuple[TextChunk, float]], graph_context: str) -> str:
        """构建完整上下文"""
        parts = []
        
        # 添加书中原文（带编号，便于引用）
        if vector_results:
            parts.append("## 📖 书中相关原文\n")
            for i, (chunk, score) in enumerate(vector_results):
                if score > 0.3:
                    parts.append(f"**[{i+1}] 来源：{chunk.chapter}**")
                    parts.append(f"> {chunk.text[:500]}...")
                    parts.append("")
        
        # 添加图谱信息
        if graph_context:
            parts.append("\n## 🔗 知识图谱中的相关概念\n")
            parts.append(graph_context)
        
        return "\n".join(parts)
    
    def _generate_answer(self, question: str, context: str, vector_results: List[Tuple[TextChunk, float]], history: List[Dict] = None) -> str:
        """生成带引用的回答（支持多轮对话）"""
        
        # 构建对话历史部分
        history_text = ""
        if history and len(history) > 0:
            history_text = "\n## 📜 对话历史\n"
            # 只保留最近3轮对话（6条消息）
            recent_history = history[-6:]
            for msg in recent_history:
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")[:300]  # 截断过长的内容
                # 清理 HTML 标签
                import re
                content = re.sub(r'<[^>]+>', '', content)
                history_text += f"**{role}**: {content}\n\n"
        
        prompt = f"""你是一位精通查理·芒格思想的专家。请根据以下信息回答用户的问题。
{history_text}
## 参考信息
{context}

## 当前问题
{question}

## 回答要求
1. **注意对话上下文**：如果用户的问题涉及到之前的对话内容，请结合上下文理解用户意图
2. **必须引用书中原文**：在引用时使用 [1]、[2] 等标记对应上面的来源编号
3. 使用 Markdown 格式组织回答，包括：
   - 使用 `>` 引用书中的重要原话
   - 使用 `**粗体**` 强调关键概念
   - 使用列表组织要点
4. 结合知识图谱中的关系进行深度分析
5. 回答要准确、有深度、有条理
6. 如果用户在追问或要求展开，请基于之前的回答进行深入
7. 如果信息不足，请诚实说明

请用中文回答："""

        try:
            if hasattr(self.llm, 'complete'):
                response = self.llm.complete(prompt)
                if hasattr(response, 'text'):
                    return response.text
                return str(response)
            else:
                return self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"生成回答时出错: {e}"

