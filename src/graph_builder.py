"""
知识图谱构建模块
负责从文本中提取实体和关系，构建图谱
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict

import networkx as nx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from tqdm import tqdm

from .schema import (
    Entity, Relationship, Triple,
    EntityType, RelationType,
    EXTRACTION_PROMPT, CORE_CONCEPTS, COGNITIVE_BIASES
)

console = Console()


class TextChunker:
    """文本分块器"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, chapter_name: str = "") -> List[Dict]:
        """将文本分块"""
        chunks = []
        
        # 按段落分割，尽量保持语义完整
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chapter": chapter_name,
                        "index": len(chunks)
                    })
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chapter": chapter_name,
                "index": len(chunks)
            })
        
        return chunks
    
    def chunk_by_chapters(self, text: str) -> List[Dict]:
        """按章节分块（假设用 ## 或 # 标记章节）"""
        chapters = re.split(r'\n#{1,2}\s+', text)
        all_chunks = []
        
        for i, chapter in enumerate(chapters):
            if not chapter.strip():
                continue
            
            # 提取章节标题
            lines = chapter.split('\n')
            title = lines[0].strip() if lines else f"章节{i}"
            content = '\n'.join(lines[1:]) if len(lines) > 1 else chapter
            
            chunks = self.chunk_text(content, title)
            all_chunks.extend(chunks)
        
        return all_chunks


class EntityExtractor:
    """实体关系提取器"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def extract_from_chunk(self, chunk: Dict) -> Tuple[List[Entity], List[Relationship]]:
        """从单个块中提取实体和关系"""
        prompt = EXTRACTION_PROMPT.format(text=chunk["text"])
        
        try:
            # 调用 LLM
            if hasattr(self.llm, 'complete'):
                response = self.llm.complete(prompt)
                if hasattr(response, 'text'):
                    response_text = response.text
                else:
                    response_text = str(response)
            else:
                response_text = self.llm.chat([{"role": "user", "content": prompt}])
            
            # 解析 JSON
            entities, relationships = self._parse_response(response_text, chunk)
            return entities, relationships
            
        except Exception as e:
            console.print(f"[red]提取失败: {e}[/red]")
            return [], []
    
    def _parse_response(self, response: str, chunk: Dict) -> Tuple[List[Entity], List[Relationship]]:
        """解析 LLM 响应"""
        entities = []
        relationships = []
        
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                # 解析实体
                for e in data.get("entities", []):
                    entity = Entity(
                        name=e.get("name", ""),
                        entity_type=self._map_entity_type(e.get("type", "")),
                        description=e.get("description", ""),
                        source_chapter=chunk.get("chapter", "")
                    )
                    entities.append(entity)
                
                # 解析关系
                for r in data.get("relationships", []):
                    rel = Relationship(
                        source=r.get("source", ""),
                        target=r.get("target", ""),
                        relation_type=self._map_relation_type(r.get("type", "")),
                        description=r.get("description", ""),
                        source_text=chunk.get("text", "")[:200]
                    )
                    relationships.append(rel)
                    
        except json.JSONDecodeError as e:
            console.print(f"[yellow]JSON 解析警告: {e}[/yellow]")
        
        return entities, relationships
    
    def _map_entity_type(self, type_str: str) -> EntityType:
        """映射实体类型字符串到枚举"""
        type_map = {
            "概念": EntityType.CONCEPT,
            "思维模型": EntityType.MENTAL_MODEL,
            "原则": EntityType.PRINCIPLE,
            "人物": EntityType.PERSON,
            "公司": EntityType.COMPANY,
            "案例": EntityType.CASE_STUDY,
            "书籍": EntityType.BOOK,
            "学科": EntityType.DISCIPLINE,
            "认知偏误": EntityType.COGNITIVE_BIAS,
        }
        return type_map.get(type_str, EntityType.CONCEPT)
    
    def _map_relation_type(self, type_str: str) -> RelationType:
        """映射关系类型字符串到枚举"""
        type_map = {
            "解释": RelationType.EXPLAINS,
            "应用于": RelationType.APPLIES_TO,
            "源自": RelationType.DERIVED_FROM,
            "相关": RelationType.RELATED_TO,
            "受影响于": RelationType.INFLUENCED_BY,
            "合作": RelationType.COLLABORATED_WITH,
            "提及": RelationType.MENTIONED,
            "支持": RelationType.SUPPORTS,
            "反对": RelationType.OPPOSES,
            "警告": RelationType.WARNS_AGAINST,
            "是一种": RelationType.IS_A,
            "属于": RelationType.PART_OF,
            "导致": RelationType.LEADS_TO,
        }
        return type_map.get(type_str, RelationType.RELATED_TO)


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
    
    def add_entity(self, entity: Entity):
        """添加实体"""
        self.entities[entity.name] = entity
        self.graph.add_node(
            entity.name,
            entity_type=entity.entity_type.value,
            description=entity.description,
            chapter=entity.source_chapter
        )
    
    def add_relationship(self, rel: Relationship):
        """添加关系"""
        self.relationships.append(rel)
        self.graph.add_edge(
            rel.source,
            rel.target,
            relation_type=rel.relation_type.value,
            description=rel.description,
            weight=rel.weight
        )
    
    def add_core_concepts(self):
        """添加核心概念"""
        for concept in CORE_CONCEPTS:
            self.add_entity(concept)
        
        for bias in COGNITIVE_BIASES:
            self.add_entity(bias)
            # 添加与"人类误判心理学"的关系
            self.add_relationship(Relationship(
                source=bias.name,
                target="人类误判心理学",
                relation_type=RelationType.PART_OF,
                description=f"{bias.name}是25种误判心理之一"
            ))
    
    def get_stats(self) -> Dict:
        """获取图谱统计信息"""
        return {
            "节点数": self.graph.number_of_nodes(),
            "边数": self.graph.number_of_edges(),
            "实体类型分布": self._get_entity_type_distribution(),
            "关系类型分布": self._get_relation_type_distribution(),
        }
    
    def _get_entity_type_distribution(self) -> Dict:
        """获取实体类型分布"""
        dist = {}
        for name, entity in self.entities.items():
            t = entity.entity_type.value
            dist[t] = dist.get(t, 0) + 1
        return dist
    
    def _get_relation_type_distribution(self) -> Dict:
        """获取关系类型分布"""
        dist = {}
        for rel in self.relationships:
            t = rel.relation_type.value
            dist[t] = dist.get(t, 0) + 1
        return dist
    
    def find_paths(self, source: str, target: str, max_length: int = 4) -> List[List[str]]:
        """查找两个实体之间的路径"""
        try:
            paths = list(nx.all_simple_paths(
                self.graph, source, target, cutoff=max_length
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []
    
    def get_neighbors(self, entity_name: str, depth: int = 1) -> Dict:
        """获取实体的邻居"""
        if entity_name not in self.graph:
            return {}
        
        neighbors = {"in": [], "out": []}
        
        # 入边（指向该实体的）
        for pred in self.graph.predecessors(entity_name):
            edge_data = self.graph.get_edge_data(pred, entity_name)
            neighbors["in"].append({
                "entity": pred,
                "relation": edge_data.get("relation_type", "")
            })
        
        # 出边（从该实体出发的）
        for succ in self.graph.successors(entity_name):
            edge_data = self.graph.get_edge_data(entity_name, succ)
            neighbors["out"].append({
                "entity": succ,
                "relation": edge_data.get("relation_type", "")
            })
        
        return neighbors
    
    def save(self, output_dir: Path):
        """保存图谱"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为 GraphML
        nx.write_graphml(self.graph, output_dir / "knowledge_graph.graphml")
        
        # 保存实体列表
        entities_data = [
            {
                "name": e.name,
                "type": e.entity_type.value,
                "description": e.description,
                "chapter": e.source_chapter
            }
            for e in self.entities.values()
        ]
        with open(output_dir / "entities.json", "w", encoding="utf-8") as f:
            json.dump(entities_data, f, ensure_ascii=False, indent=2)
        
        # 保存关系列表
        rels_data = [
            {
                "source": r.source,
                "target": r.target,
                "type": r.relation_type.value,
                "description": r.description
            }
            for r in self.relationships
        ]
        with open(output_dir / "relationships.json", "w", encoding="utf-8") as f:
            json.dump(rels_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]图谱已保存到 {output_dir}[/green]")
    
    def load(self, input_dir: Path):
        """加载图谱"""
        input_dir = Path(input_dir)
        
        # 加载 GraphML
        graphml_path = input_dir / "knowledge_graph.graphml"
        if graphml_path.exists():
            self.graph = nx.read_graphml(graphml_path)
        
        # 加载实体
        entities_path = input_dir / "entities.json"
        if entities_path.exists():
            with open(entities_path, "r", encoding="utf-8") as f:
                entities_data = json.load(f)
            for e in entities_data:
                entity = Entity(
                    name=e["name"],
                    entity_type=EntityType(e["type"]),
                    description=e.get("description", ""),
                    source_chapter=e.get("chapter", "")
                )
                self.entities[entity.name] = entity
        
        console.print(f"[green]图谱已从 {input_dir} 加载[/green]")


class GraphBuilder:
    """图谱构建器"""
    
    def __init__(self, llm, config):
        self.llm = llm
        self.config = config
        self.chunker = TextChunker(
            chunk_size=config.processing.chunk_size,
            chunk_overlap=config.processing.chunk_overlap
        )
        self.extractor = EntityExtractor(llm)
        self.graph = KnowledgeGraph()
    
    def build_from_text(self, text: str, add_core: bool = True) -> KnowledgeGraph:
        """从文本构建图谱"""
        console.print("[bold cyan]开始构建知识图谱...[/bold cyan]")
        
        # 添加核心概念
        if add_core:
            console.print("添加核心概念...")
            self.graph.add_core_concepts()
        
        # 分块
        console.print("文本分块中...")
        chunks = self.chunker.chunk_by_chapters(text)
        console.print(f"共 {len(chunks)} 个文本块")
        
        # 提取实体和关系
        console.print("提取实体和关系...")
        for chunk in tqdm(chunks, desc="处理中"):
            entities, relationships = self.extractor.extract_from_chunk(chunk)
            
            for entity in entities:
                self.graph.add_entity(entity)
            
            for rel in relationships:
                self.graph.add_relationship(rel)
        
        # 打印统计
        stats = self.graph.get_stats()
        console.print("\n[bold green]图谱构建完成！[/bold green]")
        console.print(f"  节点数: {stats['节点数']}")
        console.print(f"  边数: {stats['边数']}")
        
        return self.graph
    
    def build_from_file(self, file_path: Path, add_core: bool = True) -> KnowledgeGraph:
        """从文件构建图谱"""
        file_path = Path(file_path)
        
        if file_path.suffix == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_path.suffix == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif file_path.suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join(page.extract_text() for page in reader.pages)
        else:
            raise ValueError(f"不支持的文件格式: {file_path.suffix}")
        
        return self.build_from_text(text, add_core)

