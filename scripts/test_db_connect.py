#!/usr/bin/env python3
"""Small utility: parse DATABASE_URL/POSTGRES_URL from repo .env.local and test TCP connectivity to the DB host:port.

This script will NOT print secrets. It prints host:port and whether a TCP connection was possible.
"""
from urllib.parse import urlparse
import os
import socket

CANDIDATES = ["DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING", "POSTGRES_URL_NO_SSL"]

def load_env(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path, "r", encoding="utf8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('\"').strip("'")
            data[k] = v
    return data

# Prefer frontend .env.local then repo root
paths = [
    os.path.join(os.path.dirname(__file__), "..", "frontend", "ai-chatbot", ".env.local"),
    os.path.join(os.path.dirname(__file__), "..", ".env.local"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
]

env = {}
for p in paths:
    p = os.path.abspath(p)
    env.update(load_env(p))

selected = None
for name in CANDIDATES:
    val = env.get(name) or os.environ.get(name)
    if val:
        selected = (name, val)
        break

if not selected:
    print("No DATABASE_URL/POSTGRES_URL found in .env.local or environment.")
    raise SystemExit(2)

name, url = selected
parsed = urlparse(url)
host = parsed.hostname or ""
port = parsed.port or 5432
print(f"Testing TCP connection to DB ({name}) at {host}:{port} (timeout=5s)")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
try:
    s.connect((host, port))
    s.close()
    print("TCP connection successful: port is reachable")
    raise SystemExit(0)
except Exception as exc:
    print(f"TCP connection failed: {exc}")
    raise SystemExit(1)
