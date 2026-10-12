from assent_worker.main import WorkerSettings, ping


async def test_ping_job_echoes() -> None:
    assert await ping({}, "hello") == "pong: hello"


def test_ping_is_registered() -> None:
    assert ping in WorkerSettings.functions
