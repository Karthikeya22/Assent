"""VCR-style cassettes for LLM calls (BUILD_PLAN §4): record once, replay free and deterministic."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from assent_agents.llm import StructuredLLM

Mode = Literal["replay", "record", "auto"]


class MissingCassette(LookupError):
    pass


def call_key(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> str:
    blob = json.dumps(
        {"tier": tier, "messages": messages, "schema": schema.__name__},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


class Cassette:
    """Wraps a StructuredLLM. One JSON file per call under `root`, named by the call key."""

    def __init__(self, root: Path, inner: StructuredLLM | None = None, mode: Mode = "auto") -> None:
        self.root, self.inner, self.mode = root, inner, mode
        self.hits = self.misses = 0

    async def __call__(self, tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        path = self.root / f"{call_key(tier, messages, schema)}.json"
        if path.exists() and self.mode != "record":
            self.hits += 1
            return schema.model_validate_json(json.loads(path.read_text("utf-8"))["response"])
        if self.mode == "replay" or self.inner is None:
            raise MissingCassette(f"no cassette for {schema.__name__} call {path.name}")
        self.misses += 1
        out = await self.inner(tier, messages, schema)
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "tier": tier,
                    "schema": schema.__name__,
                    "messages": messages,
                    "response": out.model_dump_json(),
                },
                indent=1,
                ensure_ascii=False,
            ),
            "utf-8",
            newline="\n",
        )
        return out
