"""
查询引擎模块
支持基于图谱的智能问答
"""

import json
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .graph_builder import KnowledgeGraph

console = Console()


class GraphQueryEngine:
    """图谱查询引擎"""
    
    def __init__(self, graph: KnowledgeGraph, llm):
        self.graph = graph
        self.llm = llm
    
    def query(self, question: str) -> str:
        """处理用户问题"""
        console.print(f"\n[bold cyan]问题:[/bold cyan] {question}")
        
        # 1. 从问题中提取关键实体
        entities = self._extract_question_entities(question)
        console.print(f"[dim]识别到的实体: {entities}[/dim]")
        
        # 2. 从图谱中检索相关信息
        context = self._retrieve_context(entities)
        
        # 3. 生成回答
        answer = self._generate_answer(question, context)
        
        return answer
    
    def _extract_question_entities(self, question: str) -> List[str]:
        """从问题中提取实体"""
        prompt = f"""从以下问题中提取关键实体（人名、概念、公司名等）。
只返回实体名称列表，用逗号分隔。

问题: {question}

实体列表:"""
        
        try:
            if hasattr(self.llm, 'complete'):
                response = self.llm.complete(prompt)
                if hasattr(response, 'text'):
                    response_text = response.text
                else:
                    response_text = str(response)
            else:
                response_text = self.llm.chat([{"role": "user", "content": prompt}])
            
            # 解析实体列表
            entities = [e.strip() for e in response_text.split(",") if e.strip()]
            return entities
        except Exception as e:
            console.print(f"[yellow]实体提取失败: {e}[/yellow]")
            return []
    
    def _retrieve_context(self, entities: List[str]) -> Dict:
        """从图谱中检索上下文"""
        context = {
            "entities": [],
            "relationships": [],
            "paths": []
        }
        
        for entity_name in entities:
            # 模糊匹配图谱中的实体
            matched = self._fuzzy_match_entity(entity_name)
            if matched:
                # 获取实体信息
                if matched in self.graph.entities:
                    entity = self.graph.entities[matched]
                    context["entities"].append({
                        "name": entity.name,
                        "type": entity.entity_type.value,
                        "description": entity.description
                    })
                
                # 获取邻居关系
                neighbors = self.graph.get_neighbors(matched)
                for direction, rels in neighbors.items():
                    for rel in rels:
                        context["relationships"].append({
                            "from": matched if direction == "out" else rel["entity"],
                            "to": rel["entity"] if direction == "out" else matched,
                            "relation": rel["relation"]
                        })
        
        # 如果有多个实体，尝试查找它们之间的路径
        if len(entities) >= 2:
            for i in range(len(entities) - 1):
                source = self._fuzzy_match_entity(entities[i])
                target = self._fuzzy_match_entity(entities[i + 1])
                if source and target:
                    paths = self.graph.find_paths(source, target)
                    for path in paths[:3]:  # 最多3条路径
                        context["paths"].append(path)
        
        return context
    
    def _fuzzy_match_entity(self, query: str) -> Optional[str]:
        """模糊匹配实体名称"""
        query_lower = query.lower()
        
        # 精确匹配
        if query in self.graph.entities:
            return query
        
        # 部分匹配
        for name in self.graph.entities.keys():
            if query_lower in name.lower() or name.lower() in query_lower:
                return name
        
        return None
    
    def _generate_answer(self, question: str, context: Dict) -> str:
        """基于上下文生成回答"""
        # 构建上下文描述
        context_text = self._format_context(context)
        
        prompt = f"""你是一位精通查理·芒格思想的专家。请根据以下知识图谱信息回答问题。

## 知识图谱上下文
{context_text}

## 用户问题
{question}

## 回答要求
1. 充分利用知识图谱中的关系信息
2. 如果图谱中有相关路径，请解释这些关联
3. 回答要准确、有深度，体现芒格的思维方式
4. 如果信息不足，请诚实说明

请回答:"""
        
        try:
            if hasattr(self.llm, 'complete'):
                response = self.llm.complete(prompt)
                if hasattr(response, 'text'):
                    return response.text
                else:
                    return str(response)
            else:
                return self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"生成回答时出错: {e}"
    
    def _format_context(self, context: Dict) -> str:
        """格式化上下文"""
        lines = []
        
        if context["entities"]:
            lines.append("### 相关实体")
            for e in context["entities"]:
                lines.append(f"- **{e['name']}** ({e['type']}): {e['description']}")
        
        if context["relationships"]:
            lines.append("\n### 相关关系")
            for r in context["relationships"]:
                lines.append(f"- {r['from']} --[{r['relation']}]--> {r['to']}")
        
        if context["paths"]:
            lines.append("\n### 关联路径")
            for path in context["paths"]:
                lines.append(f"- {' → '.join(path)}")
        
        return "\n".join(lines) if lines else "（暂无相关图谱信息）"
    
    def show_entity(self, entity_name: str):
        """显示实体详情"""
        matched = self._fuzzy_match_entity(entity_name)
        if not matched:
            console.print(f"[red]未找到实体: {entity_name}[/red]")
            return
        
        entity = self.graph.entities.get(matched)
        if entity:
            console.print(Panel(
                f"[bold]{entity.name}[/bold]\n\n"
                f"类型: {entity.entity_type.value}\n"
                f"描述: {entity.description}\n"
                f"来源: {entity.source_chapter}",
                title="实体详情"
            ))
        
        # 显示关系
        neighbors = self.graph.get_neighbors(matched)
        
        table = Table(title=f"{matched} 的关系")
        table.add_column("方向", style="cyan")
        table.add_column("关联实体", style="green")
        table.add_column("关系类型", style="yellow")
        
        for rel in neighbors.get("in", []):
            table.add_row("←", rel["entity"], rel["relation"])
        for rel in neighbors.get("out", []):
            table.add_row("→", rel["entity"], rel["relation"])
        
        console.print(table)
    
    def explore(self, start_entity: str, depth: int = 2):
        """探索图谱"""
        matched = self._fuzzy_match_entity(start_entity)
        if not matched:
            console.print(f"[red]未找到实体: {start_entity}[/red]")
            return
        
        console.print(f"\n[bold cyan]从 '{matched}' 开始探索 (深度={depth})[/bold cyan]")
        
        visited = set()
        self._explore_recursive(matched, depth, visited, 0)
    
    def _explore_recursive(self, entity: str, max_depth: int, visited: set, current_depth: int):
        """递归探索"""
        if current_depth >= max_depth or entity in visited:
            return
        
        visited.add(entity)
        indent = "  " * current_depth
        
        entity_info = self.graph.entities.get(entity)
        type_str = entity_info.entity_type.value if entity_info else "?"
        console.print(f"{indent}📌 [bold]{entity}[/bold] ({type_str})")
        
        neighbors = self.graph.get_neighbors(entity)
        for rel in neighbors.get("out", [])[:5]:  # 最多显示5个
            console.print(f"{indent}  └─[{rel['relation']}]→ {rel['entity']}")
            self._explore_recursive(rel["entity"], max_depth, visited, current_depth + 1)

