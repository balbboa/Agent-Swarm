import json
import os
from app.agents.handoff import HumanHandoffAgent, TICKETS_FILEPATH
from app.router import RouterAgent


def run(coro):
	import asyncio
	return asyncio.get_event_loop().run_until_complete(coro)


def test_handoff_creates_ticket(tmp_path, monkeypatch):
	monkeypatch.setenv("DATA_DIR", str(tmp_path))
	from importlib import reload
	import app.config as cfg
	reload(cfg)
	import app.agents.handoff as hand
	reload(hand)
	HumanHandoffAgent = hand.HumanHandoffAgent
	TICKETS_FILEPATH_LOCAL = hand.TICKETS_FILEPATH

	agent = HumanHandoffAgent()
	route, text = run(agent.handle("Please escalate to human", "u1"))
	assert route.startswith("handoff:ticket")
	assert os.path.exists(TICKETS_FILEPATH_LOCAL)
	with open(TICKETS_FILEPATH_LOCAL, "r", encoding="utf-8") as f:
		line = f.readline()
		obj = json.loads(line)
		assert obj["user_id"] == "u1"
		assert obj["message"].startswith("Please escalate")


def test_auto_redirect_after_clarifications(monkeypatch):
	# Enable auto redirect and set threshold to 1 for test
	monkeypatch.setenv("AUTO_REDIRECT_ON_FALLBACK", "1")
	monkeypatch.setenv("REDIRECT_MAX_CLARIFICATIONS", "1")
	from importlib import reload
	import app.config as cfg
	reload(cfg)
	# Prevent router from taking websearch path so we exercise clarification
	import app.router as router
	async def _fake_web_search(query: str, top_k: int = 3):
		return []
	monkeypatch.setattr(router, "web_search", _fake_web_search, raising=True)
	# Reload main to bind singletons with updated config
	import app.main as main
	reload(main)
	from fastapi.testclient import TestClient
	client = TestClient(main.app)
	# First unclear message triggers router clarification
	r1 = client.post("/chat", json={"message": "???", "user_id": "redir1"})
	assert r1.status_code == 200
	# Second unclear message should redirect to human
	r2 = client.post("/chat", json={"message": "???", "user_id": "redir1"})
	assert r2.status_code == 200
	data = r2.json()
	assert data["route"].startswith("handoff:ticket")


def test_router_escalation_by_keyword():
	r = RouterAgent()
	route, _ = run(r.handle("I want to talk to a human agent", "u2"))
	assert route.startswith("handoff")
