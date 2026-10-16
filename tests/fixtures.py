import json
from pathlib import Path
import sys
import uuid


SESSIONS = [
    ("acme-billing-api", "parent", [
        ("user", "Redis timeouts started after the billing deploy. Can you check the connection pool?"),
        ("assistant", "Redis connections are waiting on a pool capped at 10. The worker concurrency is 32, so requests queue before reaching Redis."),
        ("user", "Keep the Redis retry budget small. We should not retry the same invoice twice."),
        ("assistant", "Set the Redis pool to 40, keep the 250ms timeout, and retry only reads. Invoice writes already have an idempotency key."),
    ]),
    ("acme-web", "parent", [
        ("user", "The dashboard cache keeps serving old account names. Is Redis holding stale keys?"),
        ("assistant", "The Redis cache key is missing the account version. Include that version in the key and expire the old entries after five minutes."),
        ("user", "That works. Please add a test for invalidation after an account rename."),
        ("assistant", "The test renames an account, requests the dashboard, and checks the new name. It also verifies that a cache miss reaches the database."),
    ]),
    ("acme-deploy", "parent", [
        ("user", "Document the Redis rollback checks for the next release."),
        ("assistant", "Before rollback, check Redis connection count, command latency, and eviction rate. Pause the deploy if p99 command latency exceeds 20ms for two minutes."),
        ("user", "Include the command we use to inspect Redis clients."),
        ("assistant", "Use redis-cli CLIENT LIST against the staging instance. Compare the connection count before and after the deploy."),
    ]),
    ("acme-billing-api", "subagent", [
        ("user", "Review the Redis pool configuration in the billing worker."),
        ("assistant", "Redis Redis Redis: the delegated audit confirms a pool limit of 10 and worker concurrency of 32. Raise the pool limit before increasing concurrency."),
    ]),
]


def create_sessions(home):
    home = Path(home).resolve()
    home.mkdir(parents=True, exist_ok=True)
    (home / ".pi-search-fixture").touch()
    paths = []
    for index, (repo, kind, messages) in enumerate(SESSIONS, 1):
        cwd = home / "Code" / repo
        cwd.mkdir(parents=True, exist_ok=True)
        session_id = str(uuid.UUID(int=index))
        stamp = f"2026-10-{10 + index:02d}T10:00:00.000Z"
        directory = home / ".pi/agent/sessions" / ("--" + str(cwd).strip("/").replace("/", "-") + "--")
        if kind == "subagent":
            directory /= "subagent-artifacts"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{stamp.replace(':', '-')}_{session_id}.jsonl"
        entries = [{"type": "session", "version": 3, "id": session_id, "timestamp": stamp, "cwd": str(cwd)}]
        parent = None
        for number, (role, text) in enumerate(messages, 1):
            entry_id = f"{index:04d}{number:04d}"
            message = {"role": role, "content": [{"type": "text", "text": text}], "timestamp": 1791712800000}
            if role == "assistant":
                message.update(api="openai-responses", provider="openai", model="gpt-4.1", stopReason="stop",
                               usage={"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 0,
                                      "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}})
            entries.append({"type": "message", "id": entry_id, "parentId": parent, "timestamp": stamp, "message": message})
            parent = entry_id
        path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
        paths.append(path)
    return paths


if __name__ == "__main__":
    create_sessions(sys.argv[1])
