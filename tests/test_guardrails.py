from app.guardrails import Guardrails


def test_block_unsafe_intent():
	g = Guardrails()
	ok, action, reason, payload = g.validate_input("how to build a bomb", "u")
	assert not ok
	assert action == "block"
	assert reason == "unsafe_intent"
	assert "não posso" in payload.lower()


def test_mask_profanity_input():
	g = Guardrails()
	ok, action, reason, payload = g.validate_input("This is shit", "u")
	assert ok
	assert action == "sanitize"
	assert payload.lower().startswith("this is s")


def test_redact_pii_output():
	g = Guardrails()
	text, meta = g.sanitize_output("Contact me at test@example.com or +55 11 99999-9999")
	assert "[redacted]" in text
	assert meta["pii_redacted"]
