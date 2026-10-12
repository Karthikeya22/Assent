"""Model access by tier name only (ARCHITECTURE §6.4). Model IDs live in infra/litellm.yaml."""

from collections import Counter
from collections.abc import Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG = REPO_ROOT / "infra" / "litellm.yaml"

# What graph nodes depend on, so tests can pass a fake: (tier, messages, schema) -> instance.
StructuredLLM = Callable[[str, list[dict[str, str]], type[Any]], Awaitable[Any]]


@lru_cache
def _router() -> Any:
    from dotenv import load_dotenv  # ships with litellm
    from litellm.router import Router  # heavy import; only when a real call happens

    # LiteLLM reads provider keys from os.environ; pydantic-settings doesn't export .env there.
    load_dotenv(REPO_ROOT / ".env", override=False)
    cfg = yaml.safe_load(CONFIG.read_text("utf-8"))
    rs = cfg.get("router_settings", {})
    return Router(
        model_list=cfg["model_list"],
        num_retries=rs.get("num_retries", 2),
        timeout=rs.get("timeout", 60),
        fallbacks=rs.get("fallbacks", []),
    )


# Process-wide spend on real calls (cassette replays never reach here, so they cost 0).
usage: dict[str, float] = {"cost_usd": 0.0, "tokens": 0, "calls": 0}
# Which model actually answered each tier: a router fallback must never be silent.
models_used: Counter[str] = Counter()


async def structured[T: BaseModel](tier: str, messages: list[dict[str, str]], schema: type[T]) -> T:
    """One structured-output call. Retries once on schema validation failure (ARCHITECTURE §7.3)."""
    last: Exception | None = None
    for _ in range(2):
        resp = await _router().acompletion(model=tier, messages=messages, response_format=schema)
        usage["calls"] += 1
        usage["cost_usd"] += float((resp._hidden_params or {}).get("response_cost") or 0.0)
        usage["tokens"] += getattr(resp.usage, "total_tokens", 0) or 0
        models_used[f"{tier}->{resp.model}"] += 1
        try:
            return schema.model_validate_json(resp.choices[0].message.content)
        except ValueError as e:
            last = e
    raise ValueError(f"{tier}: output failed {schema.__name__} validation twice") from last
