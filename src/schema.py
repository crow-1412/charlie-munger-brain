"""
知识图谱 Schema 定义
专为《穷查理宝典》定制的实体和关系类型
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class EntityType(str, Enum):
    """实体类型"""
    # 核心概念
    CONCEPT = "概念"           # 思维模型、原则等
    MENTAL_MODEL = "思维模型"   # 具体的思维模型
    PRINCIPLE = "原则"         # 投资/生活原则
    
    # 人物
    PERSON = "人物"            # 芒格提到的人
    COMPANY = "公司"           # 提到的公司
    
    # 案例
    CASE_STUDY = "案例"        # 投资案例、商业案例
    BOOK = "书籍"              # 推荐的书籍
    
    # 学科
    DISCIPLINE = "学科"        # 物理学、心理学等
    
    # 心理学相关
    COGNITIVE_BIAS = "认知偏误"  # 25种误判心理学


class RelationType(str, Enum):
    """关系类型"""
    # 知识关系
    EXPLAINS = "解释"           # 模型解释案例
    APPLIES_TO = "应用于"       # 原则应用于场景
    DERIVED_FROM = "源自"       # 思维模型源自学科
    RELATED_TO = "相关"         # 一般性关联
    
    # 人物关系  
    INFLUENCED_BY = "受影响于"  # 芒格受谁影响
    COLLABORATED_WITH = "合作"  # 与谁合作
    MENTIONED = "提及"          # 在演讲中提及
    
    # 观点关系
    SUPPORTS = "支持"           # 支持某观点
    OPPOSES = "反对"            # 反对某观点
    WARNS_AGAINST = "警告"      # 警告某种行为
    
    # 层级关系
    IS_A = "是一种"             # 分类关系
    PART_OF = "属于"            # 组成关系
    LEADS_TO = "导致"           # 因果关系


@dataclass
class Entity:
    """实体"""
    name: str
    entity_type: EntityType
    description: str = ""
    source_chapter: str = ""  # 来源章节
    attributes: dict = field(default_factory=dict)


@dataclass  
class Relationship:
    """关系"""
    source: str
    target: str
    relation_type: RelationType
    description: str = ""
    weight: float = 1.0  # 关系强度
    source_text: str = ""  # 原文出处


@dataclass
class Triple:
    """三元组"""
    subject: Entity
    predicate: RelationType
    object: Entity
    context: str = ""  # 上下文


# 预定义的重要实体（芒格核心概念）
CORE_CONCEPTS = [
    Entity("多元思维模型", EntityType.CONCEPT, "芒格的核心思想框架，融合多学科思维"),
    Entity("能力圈", EntityType.CONCEPT, "只在自己理解的领域投资"),
    Entity("安全边际", EntityType.PRINCIPLE, "投资时保持足够的安全空间"),
    Entity("逆向思考", EntityType.MENTAL_MODEL, "反过来想，总是反过来想"),
    Entity("复利效应", EntityType.CONCEPT, "时间的朋友，指数级增长"),
    Entity("Lollapalooza效应", EntityType.CONCEPT, "多个因素共同作用产生的巨大效应"),
]

# 25种人类误判心理学
COGNITIVE_BIASES = [
    Entity("奖励和惩罚超级反应倾向", EntityType.COGNITIVE_BIAS, "激励机制对行为的强大影响"),
    Entity("喜欢/热爱倾向", EntityType.COGNITIVE_BIAS, "人们容易偏向自己喜欢的事物"),
    Entity("讨厌/憎恨倾向", EntityType.COGNITIVE_BIAS, "对厌恶事物的非理性反应"),
    Entity("避免怀疑倾向", EntityType.COGNITIVE_BIAS, "人们倾向于快速做出决定以消除疑虑"),
    Entity("避免不一致性倾向", EntityType.COGNITIVE_BIAS, "人们抗拒改变已有观点"),
    Entity("好奇心倾向", EntityType.COGNITIVE_BIAS, "对新知识的本能追求"),
    Entity("康德式公平倾向", EntityType.COGNITIVE_BIAS, "对公平的本能追求"),
    Entity("艳羡/妒忌倾向", EntityType.COGNITIVE_BIAS, "嫉妒他人所有之物"),
    Entity("回馈倾向", EntityType.COGNITIVE_BIAS, "互惠心理"),
    Entity("受简单联想影响的倾向", EntityType.COGNITIVE_BIAS, "将不相关事物关联"),
    Entity("简单的、避免痛苦的心理否认", EntityType.COGNITIVE_BIAS, "否认不愿面对的现实"),
    Entity("自视过高的倾向", EntityType.COGNITIVE_BIAS, "高估自己的能力"),
    Entity("过度乐观倾向", EntityType.COGNITIVE_BIAS, "对未来过于乐观"),
    Entity("被剥夺超级反应倾向", EntityType.COGNITIVE_BIAS, "失去比得到更痛苦"),
    Entity("社会认同倾向", EntityType.COGNITIVE_BIAS, "从众心理"),
    Entity("对比错误反应倾向", EntityType.COGNITIVE_BIAS, "相对判断而非绝对判断"),
    Entity("压力影响倾向", EntityType.COGNITIVE_BIAS, "压力下的非理性行为"),
    Entity("错误衡量易得性倾向", EntityType.COGNITIVE_BIAS, "过度重视容易获取的信息"),
    Entity("不用就忘倾向", EntityType.COGNITIVE_BIAS, "不使用的技能会退化"),
    Entity("化学物质错误影响倾向", EntityType.COGNITIVE_BIAS, "药物和酒精对判断的影响"),
    Entity("衰老-错误影响倾向", EntityType.COGNITIVE_BIAS, "年龄对认知的影响"),
    Entity("权威-错误影响倾向", EntityType.COGNITIVE_BIAS, "盲目服从权威"),
    Entity("废话倾向", EntityType.COGNITIVE_BIAS, "说废话的倾向"),
    Entity("重视理由倾向", EntityType.COGNITIVE_BIAS, "需要理由来说服自己"),
    Entity("lollapalooza倾向", EntityType.COGNITIVE_BIAS, "多种心理倾向共同作用"),
]


# 实体提取提示词模板
EXTRACTION_PROMPT = """你是一个专门分析《穷查理宝典》的知识图谱专家。请从以下文本中提取实体和关系。

## 实体类型
- 概念/思维模型: 芒格提到的思维框架、原则、模型
- 人物: 书中提到的人物
- 公司: 提到的公司
- 案例: 投资案例、商业案例
- 学科: 涉及的学科领域
- 认知偏误: 人类误判心理学中的偏误

## 关系类型
- 解释: 模型解释现象
- 应用于: 原则应用于场景
- 源自: 思维模型源自学科
- 受影响于: 人物受谁影响
- 支持/反对: 对观点的态度
- 导致: 因果关系

## 输出格式
请以 JSON 格式输出:
```json
{
  "entities": [
    {"name": "实体名称", "type": "实体类型", "description": "描述"}
  ],
  "relationships": [
    {"source": "源实体", "target": "目标实体", "type": "关系类型", "description": "描述"}
  ]
}
```

## 待分析文本:
{text}

请提取并输出 JSON:"""

