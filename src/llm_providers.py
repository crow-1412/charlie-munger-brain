"""
多 LLM 提供商支持
支持通义千问、智谱AI、OpenAI兼容接口等
"""

from typing import Optional
from rich.console import Console

console = Console()


def get_dashscope_llm(api_key: str, model: str = "qwen-plus"):
    """获取通义千问 LLM"""
    try:
        from llama_index.llms.dashscope import DashScope, DashScopeGenerationModels
        
        # 模型映射
        model_map = {
            "qwen-turbo": DashScopeGenerationModels.QWEN_TURBO,
            "qwen-plus": DashScopeGenerationModels.QWEN_PLUS,
            "qwen-max": DashScopeGenerationModels.QWEN_MAX,
        }
        
        return DashScope(
            api_key=api_key,
            model_name=model_map.get(model, DashScopeGenerationModels.QWEN_PLUS),
        )
    except ImportError:
        # 如果没有 LlamaIndex DashScope，使用原生 SDK
        console.print("[yellow]使用原生 DashScope SDK[/yellow]")
        return DashScopeLLMWrapper(api_key, model)


def get_zhipuai_llm(api_key: str, model: str = "glm-4-flash"):
    """获取智谱AI LLM"""
    return ZhipuAILLMWrapper(api_key, model)


def get_openai_compatible_llm(api_key: str, base_url: str, model: str = "gpt-4o-mini"):
    """获取 OpenAI 兼容接口 LLM (支持 302.AI 等)"""
    from llama_index.llms.openai import OpenAI
    
    return OpenAI(
        api_key=api_key,
        api_base=base_url,
        model=model,
    )


class DashScopeLLMWrapper:
    """通义千问原生 SDK 包装器"""
    
    def __init__(self, api_key: str, model: str = "qwen-plus"):
        import dashscope
        dashscope.api_key = api_key
        self.model = model
    
    def complete(self, prompt: str) -> str:
        from dashscope import Generation
        
        response = Generation.call(
            model=self.model,
            prompt=prompt,
        )
        return response.output.text
    
    def chat(self, messages: list) -> str:
        from dashscope import Generation
        
        response = Generation.call(
            model=self.model,
            messages=messages,
        )
        return response.output.text


class ZhipuAILLMWrapper:
    """智谱AI SDK 包装器"""
    
    def __init__(self, api_key: str, model: str = "glm-4-flash"):
        from zhipuai import ZhipuAI
        self.client = ZhipuAI(api_key=api_key)
        self.model = model
    
    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    
    def chat(self, messages: list) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content


def get_llm(config):
    """根据配置获取 LLM 实例"""
    provider = config.llm.provider
    
    console.print(f"[cyan]正在初始化 LLM: {provider}[/cyan]")
    
    if provider == "dashscope":
        return get_dashscope_llm(
            config.llm.dashscope_api_key,
            config.llm.dashscope_model
        )
    elif provider == "zhipuai":
        return get_zhipuai_llm(
            config.llm.zhipuai_api_key,
            config.llm.zhipuai_model
        )
    elif provider == "openai":
        return get_openai_compatible_llm(
            config.llm.openai_api_key,
            config.llm.openai_api_base,
            config.llm.openai_model
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def get_embedding(config):
    """获取 Embedding 模型"""
    provider = config.embedding.provider
    
    console.print(f"[cyan]正在初始化 Embedding: {provider}[/cyan]")
    
    if provider == "dashscope":
        from llama_index.embeddings.dashscope import DashScopeEmbedding
        return DashScopeEmbedding(
            api_key=config.llm.dashscope_api_key,
            model_name=config.embedding.dashscope_model,
        )
    elif provider == "huggingface":
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        return HuggingFaceEmbedding(
            model_name=config.embedding.huggingface_model,
        )
    else:
        raise ValueError(f"不支持的 Embedding 提供商: {provider}")

