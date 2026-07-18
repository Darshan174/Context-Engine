from app.services import agent_adapters


async def test_version_probe_kills_a_timed_out_agent_process(monkeypatch):
    class StalledProcess:
        returncode = None

        def __init__(self):
            self.killed = False

        async def communicate(self):
            return b"", b""

        def kill(self):
            self.killed = True
            self.returncode = -9

    process = StalledProcess()

    async def create_process(*_args, **_kwargs):
        return process

    async def time_out(awaitable, *, timeout):
        assert timeout == 2.0
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(agent_adapters.asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(agent_adapters.asyncio, "wait_for", time_out)

    version = await agent_adapters._probe_version("agent", ("--version",))

    assert version is None
    assert process.killed is True
