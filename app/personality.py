def apply_personality(text: str) -> str:
	if not text:
		return text
	prefix = "😊 "
	suffix = "\n\nSe precisar de mais detalhes, é só me chamar!"
	return f"{prefix}{text.strip()} {suffix}"
