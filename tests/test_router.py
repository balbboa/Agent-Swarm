from app.router import RouterAgent


def run(coro):
	import asyncio
	return asyncio.get_event_loop().run_until_complete(coro)


def test_route_to_knowledge():
	r = RouterAgent()
	route, _ = run(r.handle("Quais as taxas da maquininha?", "u1"))
	assert route in ("knowledge", "websearch")


def test_route_to_support_login():
	r = RouterAgent()
	route, ans = run(r.handle("I can't sign in to my account.", "u1"))
	assert route == "support"
	assert "Account status" in ans or "Password reset" in ans
