from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from assent_agents.cassette import Cassette, MissingCassette


class Out(BaseModel):
    answer: str


MSGS = [{"role": "user", "content": "hi"}]


async def test_record_then_replay(tmp_path: Path) -> None:
    calls = 0

    async def real(tier: str, messages: list[dict[str, str]], schema: type[Any]) -> Any:
        nonlocal calls
        calls += 1
        return schema(answer=f"call {calls}")

    rec = Cassette(tmp_path, real, mode="auto")
    assert (await rec("fast", MSGS, Out)).answer == "call 1"
    assert (await rec("fast", MSGS, Out)).answer == "call 1"  # second time replays
    assert calls == 1 and (rec.hits, rec.misses) == (1, 1)

    replay = Cassette(tmp_path, None, mode="replay")
    assert (await replay("fast", MSGS, Out)).answer == "call 1"
    with pytest.raises(MissingCassette):
        await replay("fast", [{"role": "user", "content": "different"}], Out)
