"""CLI entry point to run the pipeline from command line."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from wildfire_crisis_demo.app.deps import get_foundry_client
from wildfire_crisis_demo.domain.models import WildfireIncidentBundle
from wildfire_crisis_demo.services.orchestrator import run_pipeline


async def main(payload_path: str) -> None:
    data = json.loads(Path(payload_path).read_text(encoding="utf-8"))
    bundle = WildfireIncidentBundle.model_validate(data)
    client = get_foundry_client()
    result = await run_pipeline(bundle, client)
    print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m wildfire_crisis_demo.cli <payload.json>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
