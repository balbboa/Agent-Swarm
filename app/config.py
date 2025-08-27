from typing import List
import os

INFINITEPAY_URLS: List[str] = [
	"https://www.infinitepay.io",
	"https://www.infinitepay.io/maquininha",
	"https://www.infinitepay.io/maquininha-celular",
	"https://www.infinitepay.io/tap-to-pay",
	"https://www.infinitepay.io/pdv",
	"https://www.infinitepay.io/receba-na-hora",
	"https://www.infinitepay.io/gestao-de-cobranca-2",
	"https://www.infinitepay.io/gestao-de-cobranca",
	"https://www.infinitepay.io/link-de-pagamento",
	"https://www.infinitepay.io/loja-online",
	"https://www.infinitepay.io/boleto",
	"https://www.infinitepay.io/conta-digital",
	"https://www.infinitepay.io/conta-pj",
	"https://www.infinitepay.io/pix",
	"https://www.infinitepay.io/pix-parcelado",
	"https://www.infinitepay.io/emprestimo",
	"https://www.infinitepay.io/cartao",
	"https://www.infinitepay.io/rendimento",
]

DATA_DIR = os.environ.get("DATA_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")))
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")

# Coerce string env flags to booleans
RAG_USE_WEB = os.environ.get("RAG_USE_WEB", "1") == "1"
USE_LLM = os.environ.get("USE_LLM", "0") == "1"

# Optional LLM configuration
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "512"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))

DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "pt-BR")

# Optional redirect policy configuration
AUTO_REDIRECT_ON_FALLBACK = os.environ.get("AUTO_REDIRECT_ON_FALLBACK", "0") == "1"
REDIRECT_MAX_CLARIFICATIONS = int(os.environ.get("REDIRECT_MAX_CLARIFICATIONS", "2"))
