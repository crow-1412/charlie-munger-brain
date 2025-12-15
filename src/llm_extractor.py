"""
使用 LLM 从书籍中提取知识
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .schema import Entity, Relationship, EntityType, RelationType

console = Console()


# 实体提取提示词
ENTITY_EXTRACTION_PROMPT = """你是一个专门分析《穷查理宝典》的知识图谱专家。请从以下文本中提取重要的实体。

## 实体类型
1. 概念 - 思维框架、投资理念（如：多元思维模型、能力圈）
2. 思维模型 - 具体的思维工具（如：逆向思考、复利效应）
3. 原则 - 投资或生活原则（如：安全边际）
4. 人物 - 书中提到的重要人物
5. 公司 - 提到的公司
6. 案例 - 投资或商业案例
7. 学科 - 涉及的学科领域
8. 认知偏误 - 人类误判心理学中的偏误

## 文本
{text}

## 输出要求
请以 JSON 数组格式输出，每个实体包含 name（名称）、type（类型）、description（简短描述）：
```json
[
  {{"name": "实体名称", "type": "实体类型", "description": "一句话描述"}}
]
```

只输出 JSON，不要其他内容。提取最重要的实体（最多15个）。"""


# 关系提取提示词
RELATION_EXTRACTION_PROMPT = """你是一个知识图谱专家。请根据以下文本和实体列表，提取实体之间的关系。

## 已知实体
{entities}

## 文本
{text}

## 关系类型
- 解释：A解释B（如：激励机制 解释 联邦快递案例）
- 应用于：A应用于B
- 源自：A源自B（如：复利思维 源自 富兰克林）
- 支持：A支持B的观点
- 反对：A反对B
- 导致：A导致B
- 属于：A属于B（如：激励机制 属于 误判心理学）
- 相关：A与B相关

## 输出要求
请以 JSON 数组格式输出，每个关系包含 source（源实体）、target（目标实体）、type（关系类型）、description（描述）：
```json
[
  {{"source": "源实体", "target": "目标实体", "type": "关系类型", "description": "描述"}}
]
```

只输出 JSON，不要其他内容。提取最重要的关系（最多10个）。"""


class LLMKnowledgeExtractor:
    """使用 LLM 提取知识（优化成本版）"""
    
    def __init__(self, llm, chunk_size: int = 3000):
        """
        Args:
            llm: LLM 实例
            chunk_size: 每块大小（增大可减少 API 调用次数）
        """
        self.llm = llm
        self.chunk_size = chunk_size
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
    
    def extract_from_file(self, file_path: str, max_chunks: int = 15) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """从文件提取知识"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.extract_from_text(text, max_chunks)
    
    def extract_from_text(self, text: str, max_chunks: int = 30) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """从文本提取知识"""
        console.print("[bold cyan]🧠 使用 LLM 从书籍中提取知识...[/bold cyan]")
        
        # 1. 分块
        chunks = self._split_into_chunks(text)
        console.print(f"📖 共 {len(chunks)} 个文本块，将处理前 {min(len(chunks), max_chunks)} 个")
        
        # 限制处理数量（避免 API 调用过多）
        chunks_to_process = chunks[:max_chunks]
        
        # 2. 逐块提取实体
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("提取实体...", total=len(chunks_to_process))
            
            for i, chunk in enumerate(chunks_to_process):
                try:
                    self._extract_entities_from_chunk(chunk, i)
                except Exception as e:
                    console.print(f"[yellow]块 {i} 提取失败: {e}[/yellow]")
                progress.update(task, advance=1)
        
        console.print(f"✅ 提取到 {len(self.entities)} 个实体")
        
        # 3. 提取关系（使用部分文本）
        console.print("\n[yellow]🔗 提取实体关系...[/yellow]")
        self._extract_relationships(chunks_to_process[:10])
        console.print(f"✅ 提取到 {len(self.relationships)} 个关系")
        
        # 4. 添加核心关系
        self._add_core_relationships()
        
        return self.entities, self.relationships
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """将文本分成块"""
        chunks = []
        
        # 按章节分割
        sections = re.split(r'\n===\s*.*?\s*===\n', text)
        
        for section in sections:
            section = section.strip()
            if len(section) < 100:
                continue
            
            # 如果章节太长，进一步分割
            if len(section) > self.chunk_size:
                paragraphs = section.split('\n\n')
                current_chunk = ""
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) < self.chunk_size:
                        current_chunk += para + "\n\n"
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = para + "\n\n"
                
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
            else:
                chunks.append(section)
        
        return chunks
    
    def _extract_entities_from_chunk(self, chunk: str, chunk_idx: int):
        """从单个块中提取实体"""
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=chunk[:2000])
        
        response = self._call_llm(prompt)
        entities = self._parse_entities(response)
        
        for e in entities:
            name = e.get('name', '').strip()
            if name and len(name) >= 2 and name not in self.entities:
                entity_type = self._map_entity_type(e.get('type', '概念'))
                self.entities[name] = Entity(
                    name=name,
                    entity_type=entity_type,
                    description=e.get('description', ''),
                    source_chapter=f"chunk_{chunk_idx}"
                )
    
    def _extract_relationships(self, chunks: List[str]):
        """提取关系（优化版：多轮提取 + 共现分析）"""
        entity_names = list(self.entities.keys())
        
        # 方法1：基于共现关系（同一段落出现的实体可能相关）
        console.print("  📊 分析共现关系...")
        all_text = "\n\n".join(chunks)
        paragraphs = all_text.split('\n\n')
        
        cooccurrence = {}
        for para in paragraphs:
            entities_in_para = [e for e in entity_names if e in para and len(e) >= 2]
            # 两两组合
            for i, e1 in enumerate(entities_in_para):
                for e2 in entities_in_para[i+1:]:
                    if e1 != e2:
                        pair = tuple(sorted([e1, e2]))
                        cooccurrence[pair] = cooccurrence.get(pair, 0) + 1
        
        # 添加共现次数>=2的关系
        for (e1, e2), count in sorted(cooccurrence.items(), key=lambda x: -x[1])[:30]:
            if count >= 2:
                self.relationships.append(Relationship(
                    source=e1,
                    target=e2,
                    relation_type=RelationType.RELATED_TO,
                    description=f"在书中共同出现 {count} 次"
                ))
        
        # 方法2：让 LLM 专门分析核心实体的关系
        console.print("  🧠 LLM 分析核心关系...")
        core_entities = entity_names[:30]  # 取前30个核心实体
        entity_list = ", ".join(core_entities)
        
        # 使用专门的关系提取提示词
        prompt = RELATION_EXTRACTION_PROMPT.format(
            entities=entity_list,
            text="\n\n".join(chunks[:3])[:3000]
        )
        
        response = self._call_llm(prompt)
        relations = self._parse_relations(response)
        
        for r in relations:
            source = r.get('source', '').strip()
            target = r.get('target', '').strip()
            
            if source in self.entities and target in self.entities and source != target:
                # 检查是否已存在
                exists = any(
                    rel.source == source and rel.target == target 
                    for rel in self.relationships
                )
                if not exists:
                    rel_type = self._map_relation_type(r.get('type', '相关'))
                    self.relationships.append(Relationship(
                        source=source,
                        target=target,
                        relation_type=rel_type,
                        description=r.get('description', '')
                    ))
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        if hasattr(self.llm, 'complete'):
            response = self.llm.complete(prompt)
            if hasattr(response, 'text'):
                return response.text
            return str(response)
        else:
            return self.llm.chat([{"role": "user", "content": prompt}])
    
    def _parse_entities(self, response: str) -> List[Dict]:
        """解析实体 JSON"""
        try:
            # 尝试找到 JSON 数组
            match = re.search(r'\[[\s\S]*\]', response)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
        return []
    
    def _parse_relations(self, response: str) -> List[Dict]:
        """解析关系 JSON"""
        try:
            match = re.search(r'\[[\s\S]*\]', response)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
        return []
    
    def _map_entity_type(self, type_str: str) -> EntityType:
        """映射实体类型"""
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
        """映射关系类型"""
        type_map = {
            "解释": RelationType.EXPLAINS,
            "应用于": RelationType.APPLIES_TO,
            "源自": RelationType.DERIVED_FROM,
            "相关": RelationType.RELATED_TO,
            "支持": RelationType.SUPPORTS,
            "反对": RelationType.OPPOSES,
            "属于": RelationType.PART_OF,
            "导致": RelationType.LEADS_TO,
            "影响": RelationType.INFLUENCED_BY,
        }
        return type_map.get(type_str, RelationType.RELATED_TO)
    
    def _add_core_relationships(self):
        """添加核心关系"""
        core_relations = [
            ("查理·芒格", "多元思维模型", "支持", "芒格是多元思维模型的核心倡导者"),
            ("查理·芒格", "沃伦·巴菲特", "相关", "长期合作伙伴"),
            ("查理·芒格", "伯克希尔·哈撒韦", "属于", "副董事长"),
            ("多元思维模型", "物理学", "源自", "借鉴物理学思维"),
            ("多元思维模型", "心理学", "源自", "借鉴心理学思维"),
            ("多元思维模型", "经济学", "源自", "借鉴经济学思维"),
        ]
        
        for source, target, rel_type, desc in core_relations:
            if source in self.entities and target in self.entities:
                self.relationships.append(Relationship(
                    source=source,
                    target=target,
                    relation_type=self._map_relation_type(rel_type),
                    description=desc
                ))

