import os
from importlib import reload


def run(coro):
	import asyncio
	return asyncio.get_event_loop().run_until_complete(coro)


def test_slack_fallback_outbox(tmp_path, monkeypatch):
	monkeypatch.setenv("DATA_DIR", str(tmp_path))
	monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
	import app.config as cfg
	reload(cfg)
	import app.agents.slack as slack
	reload(slack)
	SlackAgent = slack.SlackAgent
	OUTBOX = slack.OUTBOX_FILEPATH

	agent = SlackAgent()
	route, msg = run(agent.handle("notify team about outage", "u1"))
	assert route == "slack:fallback"
	assert os.path.exists(OUTBOX)
	with open(OUTBOX, "r", encoding="utf-8") as f:
		line = f.readline()
		assert "u1" in line
		assert "outage" in line


def test_router_slack_trigger():
	from app.router import RouterAgent
	r = RouterAgent()
	route, _ = run(r.handle("Please notify team on Slack", "u2"))
	assert route.startswith("slack:")
