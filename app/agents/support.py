from typing import Tuple, Dict, List
import logging
import random
from app.agents.base import Agent

logger = logging.getLogger(__name__)


_FAKE_DB: Dict[str, Dict[str, object]] = {}


def _ensure_user(user_id: str) -> Dict[str, object]:
	if user_id not in _FAKE_DB:
		_FAKE_DB[user_id] = {
			"status": random.choice(["active", "pending_verification", "blocked"]),
			"failed_signins": random.randint(0, 3),
			"name": f"User {user_id}",
			"email": f"{user_id}@example.com",
			"account_balance": round(random.uniform(0, 10000), 2),
			"daily_transfer_limit": 5000.0,
			"available_transfer_limit": round(random.uniform(1000, 5000), 2),
			"transactions": [
				{"id": f"tx-{i}", "amount": round(random.uniform(10, 500), 2), "status": random.choice(["settled", "pending"]) }
				for i in range(5)
			],
			"transfers": [
				{"id": f"tr-{i}", "amount": round(random.uniform(5, 1500), 2), "status": random.choice(["queued", "processing", "completed", "failed"]) }
				for i in range(random.randint(1, 3))
			],
		}
	return _FAKE_DB[user_id]


def tool_account_status(user_id: str) -> str:
	data = _ensure_user(user_id)
	return f"Account status: {data['status']}, failed sign-ins: {data['failed_signins']}"


def tool_reset_password(user_id: str) -> str:
	_ensure_user(user_id)
	return "Password reset link sent to your registered email."


def tool_recent_transactions(user_id: str, limit: int = 3) -> List[Dict[str, object]]:
	data = _ensure_user(user_id)
	return data["transactions"][:limit]


def get_user_info(user_id: str) -> str:
	data = _ensure_user(user_id)
	return (
		f"Usuário: {data['name']} ({data['email']}). "
		f"Status: {data['status']}. "
		f"Saldo: R${data['account_balance']:.2f}. "
		f"Limite de transferência: R${data['available_transfer_limit']:.2f}/R${data['daily_transfer_limit']:.2f}."
	)


def check_transfer_status(user_id: str) -> str:
	data = _ensure_user(user_id)
	transfers = data.get("transfers", [])
	if not transfers:
		return "Nenhuma transferência encontrada para este usuário."
	last = transfers[-1]
	return f"Transferência {last['id']} de R${last['amount']:.2f}: {last['status']}."


class CustomerSupportAgent(Agent):
	"""Handles basic support intents using lightweight tools over a fake DB."""
	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		lower = message.lower()
		if "sign in" in lower or "login" in lower or "signin" in lower:
			status = tool_account_status(user_id)
			# If recent failures, proactively include reset + basic tips
			if "failed" in status and "0" not in status:
				reset = tool_reset_password(user_id)
				return ("support", f"{status}. {reset}")
			# Add concise guidance when no failures are recorded
			return ("support", status)
		# User profile/info intents
		if any(k in lower for k in ["user info", "perfil", "cadastro", "meus dados", "dados da conta", "account info"]):
			return ("support", get_user_info(user_id))
		# Transfer status intents
		if "transfer" in lower or "transferir" in lower or "status da transferência" in lower:
			hint_parts: List[str] = []
			# Provide simple diagnostics based on limits/status
			data = _ensure_user(user_id)
			if data.get("status") == "blocked":
				hint_parts.append("Conta bloqueada: verifique documentação e suporte.")
			avail = float(data.get("available_transfer_limit", 0.0))
			if avail <= 0:
				hint_parts.append("Limite diário de transferência esgotado.")
			base = check_transfer_status(user_id)
			# If transfer is queued/processing, add general guidance
			if any(s in base for s in ["queued", "processing"]):
				hint_parts.append("Aguarde o processamento alguns minutos; se persistir, verifique limite diário e status da conta.")
			if hint_parts:
				base = f"{base} Dica: " + " ".join(hint_parts)
			return ("support", base)
		if "transaction" in lower or "transactions" in lower or "extrato" in lower:
			txs = tool_recent_transactions(user_id)
			items = ", ".join([f"{t['id']} R${t['amount']} {t['status']}" for t in txs])
			return ("support", f"Últimas transações: {items}")
		logger.debug("CustomerSupportAgent fallback: no support intent matched; asking for details")
		return ("support", "Posso ajudar com login, transfers, ou extrato. Pode detalhar?")
