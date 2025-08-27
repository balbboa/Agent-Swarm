import httpx
from typing import List, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs
from bs4 import BeautifulSoup

DDG_HTML = "https://html.duckduckgo.com/html/"
DDG_IA = "https://api.duckduckgo.com/"


def _normalize_url(url: str) -> str:
	try:
		parsed = urlparse(url)
		# Unwrap DuckDuckGo redirect links: https://duckduckgo.com/l/?uddg=<encoded>
		if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
			qs = parse_qs(parsed.query)
			uddg = qs.get("uddg", [None])[0]
			if uddg:
				return _normalize_url(uddg)
		if not parsed.scheme.startswith("http"):
			return ""
		if "duckduckgo.com" in parsed.netloc:
			return ""
		return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
	except Exception:
		return ""


def _extract_results_from_html(html: str) -> List[Tuple[str, str]]:
	soup = BeautifulSoup(html, "html.parser")
	results: List[Tuple[str, str]] = []
	# DuckDuckGo html endpoint uses anchors with class result__a inside .result
	for a in soup.select("a.result__a, a.result__url, a.result__title"):  # broaden selectors for robustness
		href = a.get("href") or ""
		title = a.get_text(strip=True)
		if not href:
			continue
		norm = _normalize_url(href)
		if not norm:
			continue
		if not title:
			title = norm
		results.append((title, norm))
	# De-duplicate by URL order-preserving
	seen = set()
	dedup: List[Tuple[str, str]] = []
	for title, url in results:
		if url in seen:
			continue
		seen.add(url)
		dedup.append((title, url))
	return dedup


async def _search_duckduckgo_html(client: httpx.AsyncClient, query: str) -> List[Tuple[str, str]]:
	resp = await client.get(DDG_HTML, params={"q": query}, headers={"User-Agent": "Mozilla/5.0"})
	resp.raise_for_status()
	return _extract_results_from_html(resp.text)


async def _search_duckduckgo_ia(client: httpx.AsyncClient, query: str) -> List[Tuple[str, str]]:
	# Fallback to Instant Answer API (limited but deterministic)
	resp = await client.get(DDG_IA, params={"q": query, "format": "json", "no_html": 1, "no_redirect": 1})
	resp.raise_for_status()
	data = resp.json()
	results: List[Tuple[str, str]] = []
	if data.get("AbstractURL"):
		results.append((data.get("Heading") or data.get("AbstractURL"), data["AbstractURL"]))
	for topic in data.get("RelatedTopics", [])[:5]:
		if isinstance(topic, dict) and topic.get("FirstURL"):
			title = topic.get("Text") or topic.get("FirstURL")
			results.append((title, topic["FirstURL"]))
	return results


async def web_search(query: str, top_k: int = 3) -> List[str]:
	items: List[Tuple[str, str]] = []
	try:
		async with httpx.AsyncClient(timeout=10) as client:
			try:
				items = await _search_duckduckgo_html(client, query)
			except Exception:
				items = []
			if not items:
				try:
					items = await _search_duckduckgo_ia(client, query)
				except Exception:
					items = []
	except Exception:
		items = []
	# Format as "Title (URL)" strings
	formatted = [f"{title} ({url})" for title, url in items]
	return formatted[:top_k]
