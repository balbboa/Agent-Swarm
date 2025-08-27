import os
import io
import tempfile
from app.agents.knowledge import KnowledgeAgent, BM25RAG, _simple_clean
from app.config import KNOWLEDGE_DIR
import importlib


def asyncio_run(coro):
	import asyncio
	return asyncio.get_event_loop().run_until_complete(coro)


def test_bm25_basic_retrieval(tmp_path, monkeypatch):
	# Prepare knowledge docs
	kdir = tmp_path / "knowledge"
	kdir.mkdir()
	(kdir / "a.txt").write_text("Maquininha Smart possui taxas competitivas.", encoding="utf-8")
	(kdir / "b.txt").write_text("Tap to Pay transforma seu celular em maquininha.", encoding="utf-8")

	# Redirect knowledge directory via DATA_DIR before importing modules
	monkeypatch.setenv("DATA_DIR", str(tmp_path))

	import app.config as cfg
	importlib.reload(cfg)
	import app.agents.knowledge as knowledge
	importlib.reload(knowledge)
	KnowledgeAgent = knowledge.KnowledgeAgent

	agent = KnowledgeAgent()
	route, answer = asyncio_run(agent.handle("Quais as taxas da maquininha?", "u1"))
	assert route == "knowledge"
	assert "taxas" in answer.lower() or "maquininha" in answer.lower()
