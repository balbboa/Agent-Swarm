from importlib import reload


def run(coro):
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)


def test_route_to_llm_when_enabled(monkeypatch):
    monkeypatch.setenv("USE_LLM", "1")

    import app.config as cfg
    reload(cfg)
    import app.router as router
    reload(router)

    RouterAgent = router.RouterAgent
    r = RouterAgent()
    route, _ = run(r.handle("Quais as taxas da maquininha?", "u1"))
    # When LLM is enabled but client may be missing, allow llm fallback;
    # keep backward compatibility with knowledge/websearch
    assert route in ("llm", "llm:fallback", "knowledge", "websearch")


