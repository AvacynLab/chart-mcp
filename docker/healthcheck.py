"""Docker container healthcheck probing FastAPI /health endpoint.

This lightweight script allows the Docker HEALTHCHECK instruction to
verify the application server responds with HTTP 200 without relying on
shell heredocs that some builders misinterpret.
"""

from __future__ import annotations

import http.client
import sys
from contextlib import suppress


def main() -> int:
    """Return zero when the API health endpoint responds with HTTP 200."""
    # Defer connection creation so the cleanup logic can close it safely when
    # the request or response handling fails midway through the probe.
    connection: http.client.HTTPConnection | None = None
    try:
        connection = http.client.HTTPConnection("localhost", 8000, timeout=3)
        connection.request("GET", "/health")
        response = connection.getresponse()
        return 0 if response.status == 200 else 1
    except Exception:
        return 1
    finally:
        with suppress(Exception):
            if connection is not None:
                connection.close()


if __name__ == "__main__":
    sys.exit(main())
