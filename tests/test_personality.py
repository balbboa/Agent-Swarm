from app.personality import apply_personality


def test_personality_wraps_text():
	out = apply_personality("Olá")
	assert out.startswith("😊 ")
	assert "me chamar" in out
