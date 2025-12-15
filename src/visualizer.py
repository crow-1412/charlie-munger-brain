"""
图谱可视化模块
生成交互式图谱可视化
"""

from pathlib import Path
from typing import Optional, List
from rich.console import Console

from .graph_builder import KnowledgeGraph

console = Console()


def visualize_graph(
    graph: KnowledgeGraph,
    output_path: str = "output/graph.html",
    height: str = "800px",
    width: str = "100%",
    filter_types: Optional[List[str]] = None
):
    """
    生成交互式图谱可视化
    
    Args:
        graph: 知识图谱
        output_path: 输出 HTML 文件路径
        height: 图高度
        width: 图宽度
        filter_types: 只显示指定类型的实体
    """
    try:
        from pyvis.network import Network
    except ImportError:
        console.print("[red]请先安装 pyvis: pip install pyvis[/red]")
        return
    
    # 创建网络图
    net = Network(
        height=height,
        width=width,
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True
    )
    
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
    
    # 添加节点
    for name, entity in graph.entities.items():
        entity_type = entity.entity_type.value
        
        # 类型过滤
        if filter_types and entity_type not in filter_types:
            continue
        
        color = type_colors.get(entity_type, "#95a5a6")
        
        net.add_node(
            name,
            label=name,
            title=f"{entity_type}: {entity.description}",
            color=color,
            size=25 if entity_type in ["概念", "思维模型"] else 20
        )
    
    # 添加边
    for rel in graph.relationships:
        # 检查节点是否存在
        if rel.source in [n["id"] for n in net.nodes] and rel.target in [n["id"] for n in net.nodes]:
            net.add_edge(
                rel.source,
                rel.target,
                title=rel.relation_type.value,
                label=rel.relation_type.value,
                arrows="to"
            )
    
    # 配置物理引擎
    net.set_options("""
    {
        "nodes": {
            "font": {
                "size": 14,
                "face": "Microsoft YaHei"
            }
        },
        "edges": {
            "font": {
                "size": 10,
                "face": "Microsoft YaHei",
                "align": "middle"
            },
            "smooth": {
                "type": "curvedCW",
                "roundness": 0.2
            }
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {
                "enabled": true,
                "iterations": 150
            }
        },
        "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": {
                "enabled": true
            }
        }
    }
    """)
    
    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存
    net.save_graph(str(output_path))
    console.print(f"[green]可视化图谱已保存到: {output_path}[/green]")
    console.print(f"[dim]用浏览器打开查看交互式图谱[/dim]")


def generate_summary_report(graph: KnowledgeGraph, output_path: str = "output/report.md"):
    """生成图谱摘要报告"""
    
    stats = graph.get_stats()
    
    report = f"""# 《穷查理宝典》知识图谱报告

## 📊 统计摘要

- **节点总数**: {stats['节点数']}
- **关系总数**: {stats['边数']}

## 🏷️ 实体类型分布

| 类型 | 数量 |
|------|------|
"""
    
    for entity_type, count in stats['实体类型分布'].items():
        report += f"| {entity_type} | {count} |\n"
    
    report += """
## 🔗 关系类型分布

| 关系 | 数量 |
|------|------|
"""
    
    for rel_type, count in stats['关系类型分布'].items():
        report += f"| {rel_type} | {count} |\n"
    
    # 找出最重要的节点（度数最高）
    report += "\n## 🌟 核心概念 (连接最多的节点)\n\n"
    
    degrees = [(node, graph.graph.degree(node)) for node in graph.graph.nodes()]
    top_nodes = sorted(degrees, key=lambda x: x[1], reverse=True)[:10]
    
    for i, (node, degree) in enumerate(top_nodes, 1):
        entity = graph.entities.get(node)
        type_str = entity.entity_type.value if entity else "未知"
        report += f"{i}. **{node}** ({type_str}) - {degree} 个连接\n"
    
    # 保存报告
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    console.print(f"[green]报告已保存到: {output_path}[/green]")
    
    return report

