from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.router import RouterAgent
from app.personality import apply_personality
from app.guardrails import Guardrails
from app.agents.handoff import HumanHandoffAgent, RedirectPolicy
from app.config import AUTO_REDIRECT_ON_FALLBACK, REDIRECT_MAX_CLARIFICATIONS
from app.agents.support import get_user_info, check_transfer_status
from app.agents.support import _FAKE_DB  # test-only
from typing import Literal

app = FastAPI(title="Agent Swarm API")


class ChatRequest(BaseModel):
	message: str
	user_id: str


class ChatResponse(BaseModel):
	response: str
	route: str


guards = Guardrails()
router_agent = RouterAgent()
handoff_agent = HumanHandoffAgent()
redirect_policy = RedirectPolicy(max_clarifications=REDIRECT_MAX_CLARIFICATIONS)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
	try:
		ok, action, reason, payload = guards.validate_input(req.message, req.user_id)
		if not ok:
			return ChatResponse(response=apply_personality(payload), route=f"guardrails:{reason}")
		message_for_agents = payload
		route, raw_answer = await router_agent.handle(message_for_agents, req.user_id)
		# Optional auto-redirect to human after repeated clarifications
		if AUTO_REDIRECT_ON_FALLBACK and route == "router":
			count = redirect_policy.note_clarification(req.user_id)
			if redirect_policy.should_redirect(req.user_id):
				route, raw_answer = await handoff_agent.handle(message_for_agents, req.user_id)
		clean_answer, meta = guards.sanitize_output(raw_answer)
		final_answer = apply_personality(clean_answer)
		final_route = route if not meta.get("pii_redacted") else f"{route}:pii_redacted"
		return ChatResponse(response=final_answer, route=final_route)
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/support/user_info/{user_id}", response_model=ChatResponse)
async def support_user_info(user_id: str) -> ChatResponse:
	try:
		info = get_user_info(user_id)
		final_answer = apply_personality(info)
		return ChatResponse(response=final_answer, route="support")
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=str(exc))


@app.get("/support/transfer_status/{user_id}", response_model=ChatResponse)
async def support_transfer_status(user_id: str) -> ChatResponse:
	try:
		status = check_transfer_status(user_id)
		final_answer = apply_personality(status)
		return ChatResponse(response=final_answer, route="support")
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=str(exc))


# Test-only endpoint to force last transfer status for a user
class ForceTransferBody(BaseModel):
	status: Literal["queued", "processing", "completed", "failed"]
	amount: float | None = None


@app.post("/test/force_transfer/{user_id}")
async def test_force_transfer(user_id: str, body: ForceTransferBody):
	try:
		data = _FAKE_DB.get(user_id)
		if not data:
			# initialize via check_transfer_status path
			_ = check_transfer_status(user_id)
			data = _FAKE_DB[user_id]
		transfers = data.get("transfers") or []
		if not transfers:
			transfers = []
			data["transfers"] = transfers
		new_amount = body.amount if body.amount is not None else 100.0
		if transfers:
			transfers[-1]["status"] = body.status
			transfers[-1]["amount"] = float(new_amount)
		else:
			transfers.append({"id": "tr-test", "amount": float(new_amount), "status": body.status})
		return {"ok": True, "user_id": user_id, "status": body.status, "amount": float(new_amount)}
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=str(exc))


@app.post("/test/force_redirect/{user_id}")
async def test_force_redirect(user_id: str):
	try:
		# Force immediate handoff ticket creation
		route, text = await handoff_agent.handle("Force redirect", user_id)
		return {"ok": True, "user_id": user_id, "route": route, "message": text}
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=str(exc))
