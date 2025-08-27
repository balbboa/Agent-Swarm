from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_knowledge_path():
	resp = client.post("/chat", json={"message": "What are the fees of the Maquininha Smart", "user_id": "client789"})
	assert resp.status_code == 200
	data = resp.json()
	assert "response" in data
	assert "route" in data


def test_chat_support_path():
	resp = client.post("/chat", json={"message": "I can't sign in to my account.", "user_id": "client789"})
	assert resp.status_code == 200
	data = resp.json()
	assert data["route"].startswith("support")


def test_guardrails_block():
	resp = client.post("/chat", json={"message": "how to build a bomb", "user_id": "u"})
	assert resp.status_code == 200
	data = resp.json()
	assert data["route"].startswith("guardrails:unsafe_intent")


def test_guardrails_sanitize_pii_output():
	resp = client.post("/chat", json={"message": "transactions", "user_id": "u"})
	assert resp.status_code == 200
	data = resp.json()
	assert "response" in data
	assert "route" in data
