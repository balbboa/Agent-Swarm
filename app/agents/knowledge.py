from typing import List, Tuple
import logging
import os
import glob
import re

from rank_bm25 import BM25Okapi
from bs4 import BeautifulSoup
import requests

from app.config import KNOWLEDGE_DIR, RAG_USE_WEB, INFINITEPAY_URLS
from app.agents.base import Agent

logger = logging.getLogger(__name__)


def _simple_clean(text: str) -> str:
	# Normalize whitespace but preserve single line breaks to keep sentence/line boundaries
	# 1) Convert Windows newlines
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	# 2) Collapse runs of spaces/tabs
	text = re.sub(r"[\t\f\v ]+", " ", text)
	# 3) Collapse >2 newlines to 2 (paragraphs), trim spaces around newlines
	text = re.sub(r" *\n+ *", "\n", text)  # single newline boundaries
	text = re.sub(r"\n{3,}", "\n\n", text)  # limit consecutive newlines
	return text.strip()


def _tokenize(text: str) -> List[str]:
	# Simple alphanumeric tokenizer for better BM25 behavior across languages
	return [t for t in re.split(r"\W+", text.lower()) if t]


class BM25RAG:
	def __init__(self, documents: List[str]) -> None:
		self.documents = documents
		self.tokenized_corpus = [_tokenize(doc) for doc in documents]
		self.bm25 = BM25Okapi(self.tokenized_corpus)

	def search(self, query: str, k: int = 5) -> List[str]:
		tokens = _tokenize(query)
		scores = self.bm25.get_scores(tokens)
		indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
		return [self.documents[i] for i in indices]


class KnowledgeAgent(Agent):
	"""Answers business knowledge questions grounded on BM25 retrieval.

	Loads local snapshots and optionally fetches InfinitePay web pages when
	configured. Applies heuristics to extract concise, actionable summaries.
	"""
	def __init__(self) -> None:
		docs = self._load_local_knowledge()
		# Avoid unnecessary network calls if local knowledge is present
		if RAG_USE_WEB and not docs:
			web_docs = self._fetch_web_pages()
			docs.extend(web_docs)
		self.rag = BM25RAG(docs)

	def retrieve(self, query: str, k: int = 5) -> List[str]:
		return self.rag.search(query, k=k)

	def _load_local_knowledge(self) -> List[str]:
		if not os.path.isdir(KNOWLEDGE_DIR):
			return []
		paths = sorted(glob.glob(os.path.join(KNOWLEDGE_DIR, "*.txt")))
		docs: List[str] = []
		for p in paths:
			try:
				with open(p, "r", encoding="utf-8") as f:
					docs.append(_simple_clean(f.read()))
			except Exception:
				continue
		return docs

	def _fetch_web_pages(self) -> List[str]:
		docs: List[str] = []
		for url in INFINITEPAY_URLS:
			try:
				r = requests.get(url, timeout=10)
				r.raise_for_status()
				# Use raw bytes so BeautifulSoup can detect the correct charset
				soup = BeautifulSoup(r.content, "html.parser")
				text = _simple_clean(soup.get_text(separator=" "))
				docs.append(text)
			except Exception:
				continue
		return docs

	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		matches = self.rag.search(message, k=5)
		if not matches:
			logger.debug("KnowledgeAgent fallback: no retrieval matches found")
			return ("knowledge", "Desculpe, não encontrei informações relevantes nos materiais disponíveis.")

		lower = message.lower()
		if any(k in lower for k in ["taxa", "taxas", "fee", "fees", "rates", "tarifa", "tarifas"]) or ("maquininha" in lower and ("fee" in lower or "taxa" in lower or "taxas" in lower or "rates" in lower)):
			summ = self._summarize_fees(matches)
			if summ:
				return ("knowledge", summ)

		# Price/cost of device
		if any(k in lower for k in ["price", "cost", "custa", "preço", "preco"]) and ("maquininha" in lower or "smart" in lower):
			price = self._summarize_price(matches)
			if price:
				return ("knowledge", price)

		# Phone as POS (Tap to Pay / maquininha no celular)
		if any(k in lower for k in ["phone", "celular", "tap to pay", "iphone", "android"]) and any(k in lower for k in ["maquininha", "card machine", "passar cartão", "passar cartao", "aceitar cartão", "aceitar cartao", "use", "usar"]):
			phone = self._summarize_phone_pos(matches)
			if phone:
				return ("knowledge", phone)

		# General snippet extraction to avoid dumping full documents
		snippet = self._extract_snippets(message, matches, max_chars_total=800)
		if snippet:
			return ("knowledge", snippet)

		# Final fallback: heavily trimmed concatenation
		joined = "\n\n".join(matches)
		if len(joined) > 600:
			joined = joined[:600].rstrip() + "..."
		logger.debug("KnowledgeAgent fallback: returning trimmed concatenation of top matches")
		return ("knowledge", joined)

	def _summarize_fees(self, docs: List[str]) -> str:
		# Extract lines with likely fee mentions; avoid legal/long policy lines and marketing noise
		candidates: List[str] = []
		for doc in docs:
			for raw in doc.splitlines():
				line = raw.strip()
				low = line.lower()
				# Skip extremely long or legal-heavy lines
				if len(line) > 220:
					continue
				if any(k in low for k in ["cédula", "cedula", "contrato", "política", "politica", "termo", "lei", "parágrafo", "paragrafo", "cláusula", "clausula"]):
					continue
				# Skip common marketing noise that pollutes fee summaries
				if any(k in low for k in ["cashback", "taxas baixas", "compre por aproximação", "compre por aproximacao", "compre", "online"]):
					continue
				if ("%" in line or "por cento" in low) and any(k in low for k in [
					"taxa", "taxas", "débito", "debito", "crédito", "credito", "12x", "pix",
				]):
					candidates.append(line)
		if not candidates:
			return ""

		percent_re = re.compile(r"\b\d{1,2}(?:[.,]\d{1,2})?\s*%")

		def extract_percent(text: str) -> str:
			m = percent_re.search(text)
			return m.group(0).replace(" .", ".").replace(" ,", ",") if m else ""

		def pick_with(predicates: List[str], require_percent: bool = True, exclude: List[str] = None) -> str:
			exclude = exclude or []
			for c in candidates:
				low = c.lower()
				if any(e in low for e in exclude):
					continue
				if any(k in low for k in predicates):
					p = extract_percent(c) if require_percent else ""
					if not require_percent or p:
						return c
			return ""

		pix_line = pick_with(["pix", "taxa zero", "taxa 0"], require_percent=False, exclude=["cashback"])  # allow 0%
		debito_line = pick_with(["débito", "debito"], require_percent=True)
		credito_12x_line = pick_with(["12x"], require_percent=True)
		# Favor explicit à vista/1x and avoid 12x lines
		credito_vista_line = pick_with(["crédito à vista", "credito a vista", "crédito a vista", "credito à vista", "crédito 1x", "credito 1x"], require_percent=True)
		if not credito_vista_line:
			# fallback: any credit line with percent but not 12x
			credito_vista_line = pick_with(["crédito", "credito"], require_percent=True, exclude=["12x"])

		def fmt(label: str, line: str, fallback: str = "") -> str:
			if not line:
				return fallback
			p = extract_percent(line)
			return f"- {label}: {p}" if p else f"- {label}: {line}"

		parts: List[str] = ["Taxas da Maquininha Smart (referência):"]
		if pix_line:
			p = extract_percent(pix_line)
			parts.append(f"- Pix: {p or '0%'}")
		if debito_line:
			parts.append(fmt("Débito", debito_line))
		if credito_vista_line:
			parts.append(fmt("Crédito à vista", credito_vista_line))
		if credito_12x_line:
			parts.append(fmt("Crédito 12x", credito_12x_line))
		if len(parts) <= 1:
			return ""
		parts.append("Obs.: As taxas variam por faturamento e pelo plano de recebimento (na hora ou em 1 dia útil).")
		return "\n".join(parts)

	def _summarize_price(self, docs: List[str]) -> str:
		candidates: List[str] = []
		for doc in docs:
			for raw in doc.splitlines():
				line = raw.strip()
				low = line.lower()
				if not line:
					continue
				if any(k in low for k in ["12 parcelas", "12x", "r$", "custa", "quanto custa", "preço", "preco", "price", "cost", "parcelas"]):
					candidates.append(line)
		if not candidates:
			return ""
		# Rank candidates to prioritize concrete price info and avoid question-only lines
		def score(s: str) -> int:
			l = s.lower()
			sc = 0
			if "r$" in l:
				sc += 5
			if "12x" in l or "12 parcelas" in l or "parcelas" in l:
				sc += 3
			if re.search(r"\d+,\d{2}", s):
				sc += 2
			if "maquininha" in l or "smart" in l:
				sc += 1
			if "quanto custa" in l or ("preço" in l and "?" in s) or ("preco" in l and "?" in s):
				sc -= 5
			return sc
		best_line = sorted(candidates, key=lambda s: (-score(s), len(s)))[0]
		return "Preço da Maquininha Smart: " + best_line

	def _summarize_phone_pos(self, docs: List[str]) -> str:
		steps: List[str] = []
		exclude_terms = ["cashback", "compre", "online", "termos", "contrato", "condições", "condicoes", "cliente", "transações", "transacoes", "equipamentos"]
		for doc in docs:
			for raw in doc.splitlines():
				line = raw.strip()
				low = line.lower()
				if not line:
					continue
				# Drop legal/marketing/very long lines
				if any(e in low for e in exclude_terms):
					continue
				if len(line) > 160:
					continue
				# Require actionable, imperative guidance or NFC mention; avoid brand-only lines
				action_terms = [
					"aproximação", "aproximacao", "abra o app", "abra o aplicativo", "clique em vender",
					"habilite nfc", "nfc", "aceite pagamentos", "aproxime o cartão", "aproxime o cartao",
					"ative", "confirme", "selecione", "toque em vender",
				]
				if any(k in low for k in action_terms):
					# Heuristic: skip ultra-short fragments and lines without spaces (likely headings)
					if len(line) < 12 or " " not in line:
						continue
					steps.append(line)
		if steps:
			# De-duplicate while keeping order
			seen = set()
			uniq: List[str] = []
			for s in steps:
				ls = s.lower()
				if ls in seen:
					continue
				seen.add(ls)
				uniq.append(s)
			# Canonicalize into up to 3 clear steps
			canonical: List[str] = []
			joined = "\n".join(uniq).lower()
			# Step 1: NFC enablement if present
			if ("nfc" in joined) and ("habilite o nfc" not in [c.lower() for c in canonical]):
				canonical.append("Habilite o NFC no celular.")
			# Step 2: app open + identity confirmation
			if any(k in joined for k in ["abra o app", "abra o aplicativo", "confirme sua identidade"]):
				canonical.append("Abra o app e confirme sua identidade.")
			# Step 3: tap to pay action
			if any(k in joined for k in ["aproxime o cartão", "aproxime o cartao", "aproximação", "aproximacao", "aceite pagamentos"]):
				canonical.append("Aproxime o cartão para cobrar (até 12x).")
			# Backfill with remaining uniq lines if fewer than 3
			for s in uniq:
				if len(canonical) >= 3:
					break
				if s not in canonical:
					canonical.append(s)
			return "Como usar o celular como maquininha (InfiniteTap):\n- " + "\n- ".join(canonical[:3])
		return ""

	def _extract_snippets(self, query: str, docs: List[str], max_chars_total: int = 800) -> str:
		keywords = set([w for w in re.split(r"\W+", query.lower()) if w])
		# English→Portuguese mapping to improve recall
		mapping = {
			"fees": ["taxa", "taxas", "tarifa", "tarifas"],
			"rates": ["taxa", "taxas"],
			"debit": ["débito", "debito"],
			"credit": ["crédito", "credito"],
			"price": ["preço", "preco", "custa"],
			"cost": ["preço", "preco", "custa"],
			"card": ["cartão", "cartao"],
			"phone": ["celular"],
			"machine": ["maquininha"],
		}
		for k, vals in mapping.items():
			if k in keywords:
				keywords.update(vals)
		# Augment with common business terms to increase recall
		keywords.update(["infinitepay", "maquininha", "pix", "débito", "debito", "crédito", "credito", "taxa", "taxas", "fee", "fees", "12x"])  # noqa: E501
		selected: List[str] = []
		seen = set()
		total = 0
		for doc in docs:
			for raw in doc.splitlines():
				line = raw.strip()
				low = line.lower()
				if not line:
					continue
				if any(k in low for k in keywords):
					# Skip extremely long lines
					if len(line) > 280:
						line = line[:280].rstrip() + "..."
					# Deduplicate near-identical lines
					if low in seen:
						continue
					seen.add(low)
					if total + len(line) + 1 > max_chars_total:
						return "\n".join(selected)
					selected.append(line)
					total += len(line) + 1
					if total >= max_chars_total:
						return "\n".join(selected)
		if selected:
			return "\n".join(selected)
		# fallback minimal excerpt per doc
		chunks: List[str] = []
		for doc in docs:
			frag = doc[:200].strip()
			if frag:
				chunks.append(frag + ("..." if len(doc) > 200 else ""))
				if sum(len(c) for c in chunks) > max_chars_total:
					break
		return "\n\n".join(chunks)
