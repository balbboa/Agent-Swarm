from typing import List


def build_system_prompt() -> str:
    return (
        "Você é um assistente especializado nos produtos InfinitePay. "
        "Responda com base estritamente no contexto fornecido. "
        "Se a resposta não estiver no contexto, diga explicitamente que não sabe e proponha próximos passos seguros. "
        "Quando possível, cite trechos relevantes do contexto entre aspas curtas para justificar a resposta. "
        "Seja conciso, claro e útil."
    )


def build_user_prompt(query: str, chunks: List[str]) -> str:
    header = "Pergunta do usuário:\n" + query.strip()
    if not chunks:
        return header + "\n\nContexto:\n(não há contexto disponível)\n\nInstruções adicionais:\n- Se não houver contexto suficiente, responda: 'Não sei com base no contexto disponível.' e sugira o que o usuário pode fornecer."
    context = "\n\n".join(chunks)
    return (
        header
        + "\n\nContexto:\n"
        + context
        + "\n\nInstruções adicionais:\n- Cite trechos relevantes entre aspas curtas quando justificar a resposta.\n- Se a pergunta não for respondida pelo contexto, diga que não sabe e proponha próximos passos."
    )


