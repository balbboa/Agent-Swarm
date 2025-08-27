from typing import Tuple

import logging
from app.agents.base import Agent
from app.agents.knowledge import KnowledgeAgent
from app.agents.support import CustomerSupportAgent
from app.agents.handoff import HumanHandoffAgent
from app.agents.slack import SlackAgent
from app.tools.websearch import web_search
from app.config import USE_LLM
try:
    from app.agents.llm import LLMAgent  # optional
except Exception:  # pragma: no cover
    LLMAgent = None  # type: ignore

logger = logging.getLogger(__name__)


class RouterAgent(Agent):
	"""Routes user messages to specialized agents based on simple heuristics."""
	def __init__(self) -> None:
		self.knowledge = KnowledgeAgent()
		self.support = CustomerSupportAgent()
		self.handoff = HumanHandoffAgent()
		self.slack = SlackAgent()
		self.llm = LLMAgent() if (USE_LLM and LLMAgent is not None) else None

	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		"""Return (route, answer) from the selected agent or a clarification.

		Heuristic ordering: explicit Slack → business knowledge (LLM if enabled,
		otherwise BM25 knowledge) → support → explicit human handoff → web search →
		clarify.
		"""
		lower = message.lower()
		# Slack notify triggers (explicit action)
		if any(k in lower for k in ["slack", "notify team", "ping team", "notificar equipe"]):
			return await self.slack.handle(message, user_id)

		# Business knowledge
		if any(k in lower for k in [
			"maquininha", "infinitepay", "pix", "link de pagamento", "taxa", "fee", "tarifa",
			"rates", "tap to pay", "pdv", "conta", "cartao", "rendimento", "boleto", "emprestimo",
			"phone", "cell phone", "celular", "card machine", "iphone", "android", "infinitetap",
		]):
			if self.llm is not None:
				logger.debug("RouterAgent selecting LLMAgent for business knowledge query")
				return await self.llm.handle(message, user_id)
			logger.debug("RouterAgent selecting KnowledgeAgent (BM25) for business knowledge query")
			return await self.knowledge.handle(message, user_id)

		# Support
		if any(k in lower for k in [
			"transfer", "transferir", "login", "sign in", "signin", "senha", "extrato", "transactions",
			"cadastro", "perfil", "meus dados", "dados da conta", "account info", "user info",
		]):
			return await self.support.handle(message, user_id)

		# Explicit escalation triggers (avoid generic 'agent')
		if any(phrase in lower for phrase in [
			"talk to a human", "talk to human", "human agent", "transfer to human", "escalate to human",
			"falar com humano", "transfira para humano", "representative", "atendente",
		]):
			return await self.handoff.handle(message, user_id)

		# General web search
		results = await web_search(message, top_k=3)
		if results:
			return ("websearch", "Resultados relacionados: " + "; ".join(results))

		# Clarify instead of auto-escalate
		logger.debug("RouterAgent fallback: no intent match; requesting clarification")
		return ("router", "Não entendi bem o assunto. Pode reformular ou dar mais detalhes?")
