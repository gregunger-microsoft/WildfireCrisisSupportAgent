"""Thin wrapper around Azure AI Foundry Agent Service."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class FoundryClientBase(ABC):
    """Abstract interface for Foundry agent operations."""

    @abstractmethod
    async def run_agent(
        self,
        agent_name: str,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """Create agent, thread, run, return the assistant message text."""
        ...


class AzureFoundryClient(FoundryClientBase):
    """Real Azure AI Foundry client using azure-ai-projects SDK."""

    def __init__(self, endpoint: str, model: str = "gpt-4o") -> None:
        self._endpoint = endpoint
        self._model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
            self._client = AIProjectClient(
                endpoint=self._endpoint,
                credential=DefaultAzureCredential(),
            )
        return self._client

    async def run_agent(
        self,
        agent_name: str,
        system_prompt: str,
        user_message: str,
    ) -> str:
        import asyncio
        return await asyncio.to_thread(
            self._run_agent_sync, agent_name, system_prompt, user_message
        )

    def _run_agent_sync(
        self,
        agent_name: str,
        system_prompt: str,
        user_message: str,
    ) -> str:
        client = self._get_client()
        agent = client.agents.create_agent(
            model=self._model,
            name=agent_name,
            instructions=system_prompt,
        )
        try:
            thread = client.agents.threads.create()
            client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message,
            )
            run = client.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id,
            )
            if run.status != "completed":
                raise RuntimeError(
                    f"Agent run failed: {run.status} — {run.last_error}"
                )
            messages = client.agents.messages.list(thread_id=thread.id)
            # Get last assistant message
            for msg in reversed(list(messages)):
                if msg.role == "assistant":
                    return msg.content[0].text.value
            raise RuntimeError("No assistant message returned")
        finally:
            client.agents.delete_agent(agent.id)
