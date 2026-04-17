"""Dependency injection providers."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from wildfire_crisis_demo.foundry.client import AzureFoundryClient, FoundryClientBase
from wildfire_crisis_demo.foundry.fake_client import FakeFoundryClient

load_dotenv()


@lru_cache(maxsize=1)
def get_foundry_client() -> FoundryClientBase:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
    if endpoint:
        model = os.environ.get("AZURE_AI_MODEL", "gpt-4o")
        return AzureFoundryClient(endpoint=endpoint, model=model)
    return FakeFoundryClient()
