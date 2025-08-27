import os
import json
import uuid
import datetime as dt
from typing import Tuple, Dict
import logging

from app.config import DATA_DIR
from app.agents.base import Agent

logger = logging.getLogger(__name__)


TICKETS_FILEPATH = os.path.join(DATA_DIR, "tickets.jsonl")


def create_support_ticket(user_id: str, message: str, route_hint: str) -> Dict[str, str]:
	os.makedirs(DATA_DIR, exist_ok=True)
	ticket_id = f"T-{uuid.uuid4().hex[:8].upper()}"
	record = {
		"ticket_id": ticket_id,
		"user_id": user_id,
		"message": message,
		"route_hint": route_hint,
		"created_at": dt.datetime.utcnow().isoformat() + "Z",
	}
	with open(TICKETS_FILEPATH, "a", encoding="utf-8") as f:
		f.write(json.dumps(record, ensure_ascii=False) + "\n")
	return record


class HumanHandoffAgent(Agent):
	"""Escalates the conversation by creating a simple ticket for human support."""
	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		record = create_support_ticket(user_id=user_id, message=message, route_hint="handoff")
		logger.debug("HumanHandoffAgent: created ticket %s for user %s", record["ticket_id"], user_id)
		text = (
			f"Ticket criado #{record['ticket_id']}. Nosso time humano entrará em contato em breve."
		)
		return ("handoff:ticket", text)


class RedirectPolicy:
	"""In-memory redirect policy with clarification counting per user."""

	def __init__(self, max_clarifications: int) -> None:
		self.max_clarifications = max_clarifications
		self._clarify_counts: Dict[str, int] = {}

	def note_clarification(self, user_id: str) -> int:
		cnt = self._clarify_counts.get(user_id, 0) + 1
		self._clarify_counts[user_id] = cnt
		return cnt

	def should_redirect(self, user_id: str) -> bool:
		return self._clarify_counts.get(user_id, 0) >= self.max_clarifications
