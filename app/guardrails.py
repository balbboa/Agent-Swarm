import re
from typing import Tuple, Dict


class Guardrails:
	def __init__(self) -> None:
		self._block_input_patterns = [
			re.compile(r"\b(make|build|how to)\b.*\b(bomb|weapon|gun|explosive)\b", re.I),
			re.compile(r"\b(hack|bypass|break into)\b.*\b(bank|account|system)\b", re.I),
			re.compile(r"\b(kill|harm|hurt)\b.*", re.I),
		]
		self._profanity_patterns = [
			re.compile(r"\b(fuck|shit|bitch|porra|caralho)\b", re.I),
		]
		self._pii_patterns = [
			re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I),
			re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{2,3}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
		]

	def validate_input(self, message: str, user_id: str) -> Tuple[bool, str, str, str]:
		if any(p.search(message) for p in self._block_input_patterns):
			return (False, "block", "unsafe_intent", "Não posso ajudar com esse tipo de solicitação.")
		if any(p.search(message) for p in self._profanity_patterns):
			sanitized = self._mask_profanity(message)
			return (True, "sanitize", "profanity_masked", sanitized)
		return (True, "allow", "ok", message)

	def sanitize_output(self, text: str) -> Tuple[str, Dict[str, bool]]:
		redacted = text
		pii_found = False
		for pat in self._pii_patterns:
			if pat.search(redacted):
				pii_found = True
				redacted = pat.sub("[redacted]", redacted)
		return (redacted, {"pii_redacted": pii_found})

	def _mask_profanity(self, text: str) -> str:
		masked = text
		for pat in self._profanity_patterns:
			masked = pat.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), masked)
		return masked
