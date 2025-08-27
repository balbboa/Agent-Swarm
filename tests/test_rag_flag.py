from importlib import reload


def test_rag_use_web_off(monkeypatch):
    # Ensure that when RAG_USE_WEB="0", KnowledgeAgent does not attempt web fetch
    monkeypatch.setenv("RAG_USE_WEB", "0")

    import app.config as cfg
    reload(cfg)
    import app.agents.knowledge as knowledge
    reload(knowledge)

    class Spy(knowledge.KnowledgeAgent):
        def _fetch_web_pages(self):  # type: ignore[override]
            assert False, "_fetch_web_pages should not be called when RAG_USE_WEB=0"

    # Instantiate; if flag is respected, no assertion is raised
    Spy()


