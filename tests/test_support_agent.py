import asyncio
import pytest

from app.agents.support import CustomerSupportAgent


@pytest.mark.asyncio
async def test_get_user_info_intent():
	agent = CustomerSupportAgent()
	route, answer = await agent.handle("Quero ver meus dados do cadastro", user_id="u1")
	assert route == "support"
	assert "Usuário:" in answer
	assert "Saldo:" in answer


@pytest.mark.asyncio
async def test_check_transfer_status_intent():
	agent = CustomerSupportAgent()
	route, answer = await agent.handle("Qual o status da transferência?", user_id="u2")
	assert route == "support"
	assert "Transferência" in answer or "Nenhuma transferência" in answer


@pytest.mark.asyncio
async def test_recent_transactions_intent():
	agent = CustomerSupportAgent()
	route, answer = await agent.handle("mostrar extrato", user_id="u3")
	assert route == "support"
	assert "Últimas transações" in answer



