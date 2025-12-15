#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Charlie Munger's Second Brain - 穷查理宝典知识图谱
主入口文件

用法:
    python main.py build <file>    从文件构建图谱
    python main.py query           进入交互式问答
    python main.py demo            运行演示
    python main.py viz             生成可视化
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def show_banner():
    """显示欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🧠 Charlie Munger's Second Brain                           ║
║   ────────────────────────────────────                        ║
║   《穷查理宝典》GraphRAG 知识图谱系统                          ║
║                                                               ║
║   "反过来想，总是反过来想"                                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def build_graph(input_file: str, output_dir: str = "output"):
    """构建知识图谱"""
    from src.config import settings
    from src.llm_providers import get_llm
    from src.graph_builder import GraphBuilder
    from src.visualizer import visualize_graph, generate_summary_report
    
    console.print(f"\n[bold]📖 开始处理: {input_file}[/bold]")
    
    # 初始化 LLM
    llm = get_llm(settings)
    
    # 构建图谱
    builder = GraphBuilder(llm, settings)
    graph = builder.build_from_file(Path(input_file))
    
    # 保存图谱
    output_path = Path(output_dir)
    graph.save(output_path)
    
    # 生成可视化
    visualize_graph(graph, str(output_path / "graph.html"))
    
    # 生成报告
    generate_summary_report(graph, str(output_path / "report.md"))
    
    console.print("\n[bold green]✅ 图谱构建完成！[/bold green]")
    console.print(f"   - 图谱文件: {output_path / 'knowledge_graph.graphml'}")
    console.print(f"   - 可视化: {output_path / 'graph.html'}")
    console.print(f"   - 报告: {output_path / 'report.md'}")


def interactive_query(graph_dir: str = "output"):
    """交互式问答"""
    from src.config import settings
    from src.llm_providers import get_llm
    from src.graph_builder import KnowledgeGraph
    from src.query_engine import GraphQueryEngine
    
    # 加载图谱
    graph = KnowledgeGraph()
    graph.load(Path(graph_dir))
    
    # 初始化查询引擎
    llm = get_llm(settings)
    engine = GraphQueryEngine(graph, llm)
    
    console.print("\n[bold cyan]💬 进入交互式问答模式[/bold cyan]")
    console.print("[dim]输入问题开始对话，输入 'quit' 退出，'explore <实体>' 探索图谱[/dim]\n")
    
    while True:
        try:
            question = Prompt.ask("[bold yellow]你的问题[/bold yellow]")
            
            if question.lower() in ['quit', 'exit', 'q']:
                console.print("[green]再见！[/green]")
                break
            
            if question.startswith("explore "):
                entity = question[8:].strip()
                engine.explore(entity)
                continue
            
            if question.startswith("show "):
                entity = question[5:].strip()
                engine.show_entity(entity)
                continue
            
            # 处理问题
            answer = engine.query(question)
            console.print(Panel(answer, title="[bold green]回答[/bold green]", border_style="green"))
            
        except KeyboardInterrupt:
            console.print("\n[green]再见！[/green]")
            break


def run_demo():
    """运行演示"""
    from src.config import settings
    from src.llm_providers import get_llm
    from src.graph_builder import GraphBuilder, KnowledgeGraph
    from src.query_engine import GraphQueryEngine
    from src.visualizer import visualize_graph
    
    console.print("\n[bold cyan]🎯 运行演示模式[/bold cyan]")
    
    # 示例文本（《人类误判心理学》片段）
    demo_text = """
# 人类误判心理学

查理·芒格认为，人类的大脑存在许多认知偏误，这些偏误常常导致错误的判断。

## 激励机制的力量

"永远不要低估激励机制的力量。"这是芒格最著名的观点之一。他认为，如果你想改变某人的行为，
改变激励机制比说教更有效。联邦快递曾经遇到一个问题：夜班工人总是不能按时完成包裹分拣。
管理层尝试了各种方法都无效，直到他们把计时工资改成计件工资，问题立刻解决了。

## 铁锤人综合征

"手里拿着锤子的人，看什么都像钉子。"这种倾向在专业人士中尤为明显。
经济学家倾向于用经济学解释一切，心理学家则用心理学解释一切。
芒格主张采用"多元思维模型"，从多个学科借鉴思维工具。

## 复利的魔力

本杰明·富兰克林曾说复利是世界第八大奇迹。芒格深信复利的力量，不仅在投资中如此，
在知识积累、声誉建设等方面也是如此。伯克希尔·哈撒韦的成功很大程度上归功于对复利的理解。
巴菲特和芒格坚持不分红，让资金在公司内部持续复利增长。

## 社会认同

人们倾向于做周围人正在做的事情。这种从众心理在投资市场尤为危险。
1999年互联网泡沫时期，几乎所有人都在追捧科技股，芒格和巴菲特却选择袖手旁观。
他们深知，在市场疯狂时保持理性是最困难也是最重要的事情。
"""
    
    console.print("\n[yellow]使用示例文本构建图谱...[/yellow]")
    
    # 初始化 LLM
    llm = get_llm(settings)
    
    # 构建图谱
    builder = GraphBuilder(llm, settings)
    graph = builder.build_from_text(demo_text)
    
    # 保存
    output_dir = Path("output/demo")
    graph.save(output_dir)
    visualize_graph(graph, str(output_dir / "graph.html"))
    
    console.print("\n[bold green]✅ 演示图谱构建完成！[/bold green]")
    console.print(f"[dim]打开 {output_dir / 'graph.html'} 查看可视化图谱[/dim]")
    
    # 演示查询
    console.print("\n[bold cyan]📝 演示问答[/bold cyan]")
    
    engine = GraphQueryEngine(graph, llm)
    
    demo_questions = [
        "芒格对激励机制有什么看法？",
        "什么是铁锤人综合征？",
        "复利思维如何应用到投资中？",
    ]
    
    for q in demo_questions:
        answer = engine.query(q)
        console.print(Panel(answer, title=f"[green]{q}[/green]", border_style="dim"))


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="穷查理宝典 GraphRAG 知识图谱系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py demo                    运行演示
  python main.py build data/book.txt     从文件构建图谱
  python main.py query                   交互式问答
  python main.py viz output              重新生成可视化
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # build 命令
    build_parser = subparsers.add_parser("build", help="从文件构建图谱")
    build_parser.add_argument("file", help="输入文件路径 (.txt/.md/.pdf)")
    build_parser.add_argument("-o", "--output", default="output", help="输出目录")
    
    # query 命令
    query_parser = subparsers.add_parser("query", help="交互式问答")
    query_parser.add_argument("-g", "--graph", default="output", help="图谱目录")
    
    # demo 命令
    subparsers.add_parser("demo", help="运行演示")
    
    # viz 命令
    viz_parser = subparsers.add_parser("viz", help="生成可视化")
    viz_parser.add_argument("graph_dir", nargs="?", default="output", help="图谱目录")
    
    args = parser.parse_args()
    
    show_banner()
    
    if args.command == "build":
        build_graph(args.file, args.output)
    elif args.command == "query":
        interactive_query(args.graph)
    elif args.command == "demo":
        run_demo()
    elif args.command == "viz":
        from src.graph_builder import KnowledgeGraph
        from src.visualizer import visualize_graph, generate_summary_report
        
        graph = KnowledgeGraph()
        graph.load(Path(args.graph_dir))
        visualize_graph(graph, f"{args.graph_dir}/graph.html")
        generate_summary_report(graph, f"{args.graph_dir}/report.md")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

