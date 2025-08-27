from typing import Tuple
from abc import ABC, abstractmethod


class Agent(ABC):
	@abstractmethod
	async def handle(self, message: str, user_id: str) -> Tuple[str, str]:
		"""Return (route_name, answer)."""
		raise NotImplementedError
