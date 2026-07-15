#!/usr/bin/env python3
"""Run the persisted first-time setup workflow used by the dashboard."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from app.services.setup_pipeline import setup_pipeline

    run_id = await setup_pipeline.start(wait=True)
    print(f"Setup run finished: {run_id}")


if __name__ == "__main__":
    asyncio.run(main())
