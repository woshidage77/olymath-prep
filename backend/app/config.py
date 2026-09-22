from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


ProviderName = Literal["deepseek", "openai"]


def load_local_environment() -> None:
    """Load local secrets without overriding explicitly supplied environment values."""
    candidates: list[Path] = []
    configured = os.getenv("YIDUO_ENV_FILE", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend([
        Path(__file__).resolve().parents[2] / ".env",
        Path.home() / ".env",
    ])
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            load_dotenv(resolved, override=False)


@dataclass(frozen=True)
class ModelSettings:
    provider: ProviderName
    api_key: str
    base_url: str | None
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def model_settings() -> ModelSettings:
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        return ModelSettings(
            provider="deepseek",
            api_key=deepseek_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
            or "https://api.deepseek.com",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()
            or "deepseek-flash",
        )
    return ModelSettings(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        base_url=None,
        model=os.getenv("YIDUO_OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini",
    )


load_local_environment()
