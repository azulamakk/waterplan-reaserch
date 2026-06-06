from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


@dataclass
class Settings:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    cache_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("WATERPLAN_CACHE_DIR", str(Path.home() / ".waterplan" / "cache"))
        )
    )
    cache_ttl_hours: int = int(os.getenv("WATERPLAN_CACHE_TTL_HOURS", "24"))
    max_search_results: int = 5
    validation_timeout_s: int = 15
    playwright_timeout_ms: int = 20000
    default_model: str = "claude-sonnet-4-6"
    models_to_compare: List[str] = field(
        default_factory=lambda: [
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "gpt-4o",
            "gpt-4o-mini",
        ]
    )
    judge_model: str = "claude-haiku-4-5-20251001"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_model(model_id: str, temperature: float = 0.0) -> BaseChatModel:
    settings = get_settings()
    if model_id.startswith("gpt") or model_id.startswith("o1") or model_id.startswith("o3"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            api_key=settings.openai_api_key or None,
            max_retries=3,
        )
    elif model_id.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_id,
            temperature=temperature,
            api_key=settings.anthropic_api_key or None,
            max_retries=3,
        )
    else:
        # Assume Ollama for anything else (llama3.1, qwen2.5, mistral, etc.)
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model_id, temperature=temperature)
        except ImportError:
            raise ValueError(
                f"Model '{model_id}' looks like an Ollama model but langchain-ollama is not installed. "
                "Run: pip install langchain-ollama"
            )
