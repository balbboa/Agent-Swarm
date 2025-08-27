import os
import json
import datetime as dt
from typing import Tuple, Dict
import logging

import httpx

from app.config import DATA_DIR
from app.agents.base import Agent

logger = logging.getLogger(__name__)


OUTBOX_FILEPATH = os.path.join(DATA_DIR, "slack_outbox.jsonl")


def _send_webhook(text: str, webhook_url: str, timeout_seconds: float = 5.0) -> bool:
	try:
		if not webhook_url:
			return False
		with httpx.Client(timeout=timeout_seconds) as client:
			resp = client.post(webhook_url, json={"text": text})
			return 200 <= resp.status_code < 300
	except Exception:
		return False


def _write_outbox(record: Dict[str, str]) -> None:
	os.makedirs(DATA_DIR, exist_ok=True)
	with open(OUTBOX_FILEPATH, "a", encoding="utf-8") as f:
		f.write(json.dumps(record, ensure_ascii=False) + "\n")


class SlackAgent(Agent):
	"""Sends Slack notifications or queues locally when webhook is missing/unreachable."""
	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
		payload = {
			"user_id": user_id,
			"message": message,
			"created_at": dt.datetime.utcnow().isoformat() + "Z",
		}
		text = f"[AgentSwarm] From {user_id}: {message}"
		sent = _send_webhook(text, webhook_url)
		if not sent:
			logger.debug("SlackAgent fallback: webhook missing or failed; writing to outbox")
			_write_outbox(payload)
			return ("slack:fallback", "Mensagem enviada ao Slack (fila local).")
		return ("slack:notify", "Notificação enviada ao Slack com sucesso.")
