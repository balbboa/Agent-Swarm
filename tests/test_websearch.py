import pytest
import httpx
from app.tools.websearch import _extract_results_from_html, _normalize_url


def test_normalize_url_unwraps_duckduckgo_redirect():
	wrapped = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Ffoo%3Fa%3Db#frag"
	assert _normalize_url(wrapped) == "https://example.com/foo"


def test_extract_results_from_html_basic():
	html = """
	<div class="result"><a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fbar%3Fq%3Dx">Example Result</a></div>
	<div class="result"><a class="result__a" href="https://example.com/alpha?x=y">Alpha</a></div>
	"""
	items = _extract_results_from_html(html)
	assert ("Example Result", "https://example.org/bar") in items
	assert ("Alpha", "https://example.com/alpha") in items
	# Dedup and valid http only
	assert all(u.startswith("http") for _, u in items)



