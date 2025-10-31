#!/usr/bin/env bash
set -euo pipefail

HOST=${1:-127.0.0.1}
PORT=${2:-3000}
ATTEMPTS=${3:-120}
SLEEP=${4:-1}

URL="http://${HOST}:${PORT}/ping"

echo "Waiting for Next.js at $URL"
for i in $(seq 1 "$ATTEMPTS"); do
  if curl -sf "$URL" >/dev/null; then
    echo "Next.js ready after $i attempt(s)"
    exit 0
  fi
  sleep "$SLEEP"
done

echo "Next.js did not become ready after $ATTEMPTS attempts" >&2
exit 1
