"""
配置管理模块
支持从 .env 文件加载配置
"""

import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: Literal["dashscope", "zhipuai", "openai", "ark"] = "dashscope"
    
    # 通义千问
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    
    # 智谱AI
    zhipuai_api_key: str = ""
    zhipuai_model: str = "glm-4-flash"
    
    # OpenAI 兼容
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    
    # 火山方舟
    ark_api_key: str = ""
    ark_model: str = "doubao-pro-4k"


class EmbeddingConfig(BaseModel):
    """Embedding 配置"""
    provider: Literal["dashscope", "huggingface"] = "dashscope"
    dashscope_model: str = "text-embedding-v2"
    huggingface_model: str = "BAAI/bge-small-zh-v1.5"


class ProcessingConfig(BaseModel):
    """处理配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    community_resolution: float = 1.0


class Settings(BaseModel):
    """全局设置"""
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    processing: ProcessingConfig = ProcessingConfig()
    
    # 路径配置
    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    
    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置"""
        return cls(
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "dashscope"),
                dashscope_api_key=os.getenv("DASHSCOPE_API_KEYS", ""),
                dashscope_model=os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
                zhipuai_api_key=os.getenv("ZHIPUAI_API_KEY", ""),
                zhipuai_model=os.getenv("ZHIPUAI_MODEL", "glm-4-flash"),
                openai_api_key=os.getenv("API_302_KEY", os.getenv("OPENAI_API_KEY", "")),
                openai_api_base=os.getenv("OPENAI_API_BASE", "https://api.302.ai/v1"),
                openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                ark_api_key=os.getenv("ARK_API_KEY", ""),
                ark_model=os.getenv("ARK_MODEL", "doubao-pro-4k"),
            ),
            embedding=EmbeddingConfig(
                provider=os.getenv("EMBEDDING_PROVIDER", "dashscope"),
            ),
            processing=ProcessingConfig(
                chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
            ),
        )


# 全局配置实例
settings = Settings.from_env()

