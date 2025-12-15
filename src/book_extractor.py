"""
书籍知识提取模块
从《穷查理宝典》中自动提取实体和关系
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
from collections import Counter
from dataclasses import dataclass

from rich.console import Console
from rich.progress import track

from .schema import Entity, Relationship, EntityType, RelationType

console = Console()


# ===== 预定义的重要概念词典 =====
# 这些是芒格思想中的核心概念，用于辅助识别

MENTAL_MODELS = {
    "多元思维模型", "逆向思维", "逆向思考", "复利", "复利效应", "能力圈",
    "安全边际", "护城河", "机会成本", "概率思维", "费马-帕斯卡系统",
    "lollapalooza效应", "Lollapalooza", "格栅思维", "多学科思维",
    "检查清单", "双轨分析", "反过来想", "跨学科"
}

COGNITIVE_BIASES = {
    "奖励和惩罚超级反应倾向", "激励机制", "喜欢/热爱倾向", "讨厌/憎恨倾向",
    "避免怀疑倾向", "避免不一致性倾向", "好奇心倾向", "康德式公平倾向",
    "艳羡/妒忌倾向", "回馈倾向", "简单联想", "心理否认", "自视过高",
    "过度乐观", "被剥夺超级反应", "社会认同", "从众", "对比错误反应",
    "压力影响", "错误衡量易得性", "不用就忘", "化学物质错误影响",
    "衰老错误影响", "权威错误影响", "废话倾向", "重视理由倾向",
    "铁锤人综合征", "铁锤人", "误判心理学", "认知偏误"
}

IMPORTANT_PEOPLE = {
    "查理·芒格", "芒格", "沃伦·巴菲特", "巴菲特", "本杰明·富兰克林",
    "富兰克林", "本杰明·格雷厄姆", "格雷厄姆", "费雪", "菲利普·费雪",
    "亚当·斯密", "达尔文", "爱因斯坦", "牛顿", "凯恩斯", "苏格拉底",
    "柏拉图", "亚里士多德", "西塞罗", "塞内卡", "马克·吐温",
    "李录", "彼得·考夫曼"
}

COMPANIES = {
    "伯克希尔·哈撒韦", "伯克希尔", "可口可乐", "喜诗糖果", "GEICO",
    "华盛顿邮报", "美国运通", "所罗门", "通用再保险", "中美能源",
    "好市多", "Costco", "每日期刊", "威斯科金融", "蓝筹印花"
}

DISCIPLINES = {
    "物理学", "数学", "生物学", "心理学", "经济学", "会计学",
    "工程学", "统计学", "化学", "历史学", "哲学", "法学"
}


class BookKnowledgeExtractor:
    """从书籍中提取知识"""
    
    def __init__(self, llm=None):
        self.llm = llm
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
    
    def extract_from_file(self, file_path: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """从文件提取知识"""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.extract_from_text(text)
    
    def extract_from_text(self, text: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """从文本提取知识"""
        console.print("[bold cyan]📚 开始从书籍中提取知识...[/bold cyan]")
        
        # 1. 分章节
        chapters = self._split_chapters(text)
        console.print(f"📖 共 {len(chapters)} 个章节")
        
        # 2. 提取实体
        console.print("\n[yellow]🔍 提取实体...[/yellow]")
        self._extract_entities(chapters)
        console.print(f"✅ 找到 {len(self.entities)} 个实体")
        
        # 3. 提取关系
        console.print("\n[yellow]🔗 提取关系...[/yellow]")
        self._extract_relationships(chapters)
        console.print(f"✅ 找到 {len(self.relationships)} 个关系")
        
        return self.entities, self.relationships
    
    def _split_chapters(self, text: str) -> List[Dict]:
        """分割章节"""
        chapters = []
        # 按 === 标记分割
        parts = re.split(r'\n===\s*(.*?)\s*===\n', text)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                title = parts[i]
                content = parts[i + 1]
                if len(content.strip()) > 100:  # 过滤太短的章节
                    chapters.append({
                        "title": title,
                        "content": content,
                        "index": len(chapters)
                    })
        
        return chapters
    
    def _extract_entities(self, chapters: List[Dict]):
        """提取实体"""
        all_text = ' '.join(c['content'] for c in chapters)
        
        # 1. 提取思维模型
        for model in MENTAL_MODELS:
            if model in all_text:
                count = all_text.count(model)
                self._add_entity(
                    model, EntityType.MENTAL_MODEL,
                    f"芒格的核心思维模型，书中出现 {count} 次",
                    importance=count
                )
        
        # 2. 提取认知偏误
        for bias in COGNITIVE_BIASES:
            if bias in all_text:
                count = all_text.count(bias)
                self._add_entity(
                    bias, EntityType.COGNITIVE_BIAS,
                    f"人类误判心理学中的认知偏误，书中出现 {count} 次",
                    importance=count
                )
        
        # 3. 提取人物
        for person in IMPORTANT_PEOPLE:
            if person in all_text:
                count = all_text.count(person)
                if count >= 3:  # 至少出现3次
                    self._add_entity(
                        person, EntityType.PERSON,
                        f"书中重要人物，出现 {count} 次",
                        importance=count
                    )
        
        # 4. 提取公司
        for company in COMPANIES:
            if company in all_text:
                count = all_text.count(company)
                if count >= 2:
                    self._add_entity(
                        company, EntityType.COMPANY,
                        f"书中提到的公司，出现 {count} 次",
                        importance=count
                    )
        
        # 5. 提取学科
        for discipline in DISCIPLINES:
            if discipline in all_text:
                count = all_text.count(discipline)
                if count >= 3:
                    self._add_entity(
                        discipline, EntityType.DISCIPLINE,
                        f"跨学科思维涉及的学科，出现 {count} 次",
                        importance=count
                    )
        
        # 6. 使用正则提取更多概念
        self._extract_concepts_by_pattern(all_text)
        
        # 7. 提取名言/原则
        self._extract_quotes(all_text)
    
    def _extract_concepts_by_pattern(self, text: str):
        """使用模式匹配提取概念"""
        # 匹配"XXX思维"、"XXX原则"、"XXX效应"等
        patterns = [
            (r'["\']([^"\']{2,15}(?:思维|原则|效应|法则|定律|模型))["\']', EntityType.MENTAL_MODEL),
            (r'「([^」]{2,15}(?:思维|原则|效应|法则|定律|模型))」', EntityType.MENTAL_MODEL),
            (r'([一-龥]{2,8}(?:思维|原则|效应|法则|定律|模型))', EntityType.MENTAL_MODEL),
        ]
        
        for pattern, entity_type in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) <= 15 and match not in self.entities:
                    count = text.count(match)
                    if count >= 2:
                        self._add_entity(
                            match, entity_type,
                            f"从文本中提取的概念，出现 {count} 次",
                            importance=count
                        )
    
    def _extract_quotes(self, text: str):
        """提取名言作为原则"""
        # 芒格的著名语录模式
        quote_patterns = [
            r'芒格说[：:][""]([^""]{10,50})[""]',
            r'芒格认为[：:，,]([^。]{10,50})',
            r'[""]([^""]{10,40})[""][，,]——芒格',
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, text)
            for match in matches[:10]:  # 最多10条
                # 清理并截断
                quote = match.strip()[:40]
                if len(quote) > 10:
                    self._add_entity(
                        f"「{quote}」", EntityType.PRINCIPLE,
                        "芒格的智慧箴言",
                        importance=1
                    )
    
    def _add_entity(self, name: str, entity_type: EntityType, description: str, importance: int = 1):
        """添加实体"""
        # 标准化名称
        name = name.strip()
        if not name or len(name) < 2:
            return
        
        if name not in self.entities:
            self.entities[name] = Entity(
                name=name,
                entity_type=entity_type,
                description=description,
                attributes={"importance": importance}
            )
        else:
            # 更新重要性
            current = self.entities[name].attributes.get("importance", 0)
            self.entities[name].attributes["importance"] = current + importance
    
    def _extract_relationships(self, chapters: List[Dict]):
        """提取关系"""
        all_text = ' '.join(c['content'] for c in chapters)
        entity_names = set(self.entities.keys())
        
        # 关系模式
        relation_patterns = [
            # A 提出/创造 B
            (r'({})(?:提出|创造|发明|提倡|主张|强调)(?:了)?[的]?({})'.format, RelationType.SUPPORTS),
            # A 影响 B
            (r'({})(?:影响|启发|塑造)(?:了)?({})'.format, RelationType.INFLUENCED_BY),
            # A 应用于 B
            (r'({})(?:应用于|用于|适用于)({})'.format, RelationType.APPLIES_TO),
            # A 源自 B
            (r'({})(?:源自|来自|借鉴自)({})'.format, RelationType.DERIVED_FROM),
            # A 与 B 相关
            (r'({})(?:和|与|跟)({})(?:相关|有关|类似)'.format, RelationType.RELATED_TO),
            # A 导致 B
            (r'({})(?:导致|造成|引发)(?:了)?({})'.format, RelationType.LEADS_TO),
            # A 反对 B
            (r'({})(?:反对|批评|否定)({})'.format, RelationType.OPPOSES),
        ]
        
        # 共现关系：在同一段落中出现的实体可能有关联
        paragraphs = all_text.split('\n\n')
        cooccurrence = Counter()
        
        for para in paragraphs:
            entities_in_para = [e for e in entity_names if e in para]
            # 两两组合
            for i, e1 in enumerate(entities_in_para):
                for e2 in entities_in_para[i+1:]:
                    if e1 != e2:
                        pair = tuple(sorted([e1, e2]))
                        cooccurrence[pair] += 1
        
        # 添加共现次数较多的关系
        for (e1, e2), count in cooccurrence.most_common(100):
            if count >= 3:  # 至少共现3次
                self._add_relationship(e1, e2, RelationType.RELATED_TO, f"在书中共同出现 {count} 次")
        
        # 添加预定义的核心关系
        self._add_core_relationships()
    
    def _add_relationship(self, source: str, target: str, rel_type: RelationType, description: str):
        """添加关系"""
        if source in self.entities and target in self.entities and source != target:
            # 检查是否已存在
            for rel in self.relationships:
                if rel.source == source and rel.target == target:
                    return
            
            self.relationships.append(Relationship(
                source=source,
                target=target,
                relation_type=rel_type,
                description=description
            ))
    
    def _add_core_relationships(self):
        """添加核心关系"""
        core_relations = [
            # 人物关系
            ("查理·芒格", "沃伦·巴菲特", RelationType.COLLABORATED_WITH, "长期合作伙伴"),
            ("查理·芒格", "伯克希尔·哈撒韦", RelationType.PART_OF, "副董事长"),
            ("查理·芒格", "多元思维模型", RelationType.SUPPORTS, "核心倡导者"),
            ("查理·芒格", "逆向思考", RelationType.SUPPORTS, "'反过来想'的倡导者"),
            
            # 思想来源
            ("多元思维模型", "物理学", RelationType.DERIVED_FROM, "借鉴物理学思维"),
            ("多元思维模型", "心理学", RelationType.DERIVED_FROM, "借鉴心理学思维"),
            ("多元思维模型", "经济学", RelationType.DERIVED_FROM, "借鉴经济学思维"),
            ("多元思维模型", "数学", RelationType.DERIVED_FROM, "借鉴数学思维"),
            ("多元思维模型", "生物学", RelationType.DERIVED_FROM, "借鉴生物学思维"),
            
            # 投资相关
            ("安全边际", "能力圈", RelationType.RELATED_TO, "投资核心原则"),
            ("复利", "伯克希尔·哈撒韦", RelationType.APPLIES_TO, "复利是伯克希尔成功的关键"),
            
            # 认知偏误
            ("激励机制", "误判心理学", RelationType.PART_OF, "25种误判心理之一"),
            ("社会认同", "误判心理学", RelationType.PART_OF, "25种误判心理之一"),
            ("铁锤人综合征", "多元思维模型", RelationType.OPPOSES, "铁锤人是多元思维的反面"),
            
            # 人物影响
            ("本杰明·富兰克林", "查理·芒格", RelationType.INFLUENCED_BY, "芒格深受富兰克林影响"),
            ("本杰明·格雷厄姆", "沃伦·巴菲特", RelationType.INFLUENCED_BY, "巴菲特的老师"),
        ]
        
        for source, target, rel_type, desc in core_relations:
            # 处理别名
            source = self._normalize_name(source)
            target = self._normalize_name(target)
            self._add_relationship(source, target, rel_type, desc)
    
    def _normalize_name(self, name: str) -> str:
        """标准化名称（处理别名）"""
        aliases = {
            "芒格": "查理·芒格",
            "巴菲特": "沃伦·巴菲特",
            "富兰克林": "本杰明·富兰克林",
            "格雷厄姆": "本杰明·格雷厄姆",
            "伯克希尔": "伯克希尔·哈撒韦",
        }
        # 如果原名在实体中，直接返回
        if name in self.entities:
            return name
        # 尝试别名
        if name in aliases and aliases[name] in self.entities:
            return aliases[name]
        # 尝试反向查找
        for alias, full_name in aliases.items():
            if name == full_name and alias in self.entities:
                return alias
        return name


def extract_knowledge_from_book(book_path: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
    """从书籍提取知识的便捷函数"""
    extractor = BookKnowledgeExtractor()
    return extractor.extract_from_file(book_path)

