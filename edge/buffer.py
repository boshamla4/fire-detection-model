"""
Local event buffer for offline (zone blanche) operation.
Events are stored as JSON lines in a local file and flushed to Supabase on reconnect.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional


BUFFER_FILE = Path(__file__).parent / ".event_buffer.jsonl"


def enqueue(event: dict) -> None:
    event["buffered_at"] = time.time()
    with open(BUFFER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def flush(supabase_client) -> int:
    """
    Attempt to flush all buffered events to Supabase.
    Returns the number of events successfully flushed.
    """
    if not BUFFER_FILE.exists():
        return 0

    lines = BUFFER_FILE.read_text(encoding="utf-8").splitlines()
    if not lines:
        return 0

    flushed = 0
    remaining = []

    for line in lines:
        try:
            event = json.loads(line)
            event.pop("buffered_at", None)
            supabase_client.table("detection_events").insert(event).execute()
            flushed += 1
        except Exception:
            remaining.append(line)

    if remaining:
        BUFFER_FILE.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    else:
        BUFFER_FILE.unlink(missing_ok=True)

    return flushed


def size() -> int:
    if not BUFFER_FILE.exists():
        return 0
    return sum(1 for _ in BUFFER_FILE.open(encoding="utf-8"))
