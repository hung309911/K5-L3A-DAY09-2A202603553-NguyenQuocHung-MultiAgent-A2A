"""Send a real A2A request and print the propagated correlation IDs."""

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from common.a2a_client import delegate

load_dotenv(Path(__file__).resolve().parent / ".env")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("CUSTOMER_AGENT_URL", "http://127.0.0.1:10100"))
    parser.add_argument("--question", default="If a company breaks a contract, avoids taxes and violates SEC compliance, what are the consequences?")
    parser.add_argument("--trace-id", default=str(uuid4()))
    parser.add_argument("--context-id", default=str(uuid4()))
    args = parser.parse_args()
    print(f"Endpoint: {args.endpoint}")
    print(f"trace_id: {args.trace_id}")
    print(f"context_id: {args.context_id}")
    print(f"Question: {args.question}")
    answer = await delegate(args.endpoint, args.question, args.context_id, args.trace_id, 0)
    if not answer:
        raise RuntimeError("Agent returned no answer")
    print("RESPONSE:")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
