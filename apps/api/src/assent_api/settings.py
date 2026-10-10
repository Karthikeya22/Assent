from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://assent:assent@localhost:5432/assent"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-dev-only-32-bytes-minimum!!"  # noqa: S105 (dev default; deploy sets JWT_SECRET)
    jwt_ttl_minutes: int = 15
    embed_dim: int = 384
    cors_origins: list[str] = ["http://localhost:3000"]
    # Agent LLM for worker runs: "openai" (real, cassette-backed) or "oracle" (benchmark patients
    # only: answers from gold, for demos and pipeline checks without an API key).
    agent_llm: str = "openai"
    chart_dir: Path = REPO_ROOT / ".data" / "bench"  # FileFhirSource root (HAPI from Phase 6)


@lru_cache
def get_settings() -> Settings:
    return Settings()
