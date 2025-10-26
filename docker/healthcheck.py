"""Docker health probe that checks the FastAPI ``/health`` endpoint.

The original implementation performed a single HTTP request which proved
too brittle for CI where the container might still be initialising the
application server when the probe runs.  The updated logic retries the
request a few times with short delays so transient start-up delays no
longer cause the job to fail.
"""

from __future__ import annotations

import http.client
import sys
import time
from contextlib import suppress

_HOST = "localhost"
_PORT = 8000
_TIMEOUT_SECONDS = 3
_RETRY_ATTEMPTS = 5
_RETRY_DELAY_SECONDS = 0.5


def _create_connection() -> http.client.HTTPConnection:
    """Return a fresh HTTP connection to the application container."""
    # Keeping the creation in a dedicated function makes it easier to stub in
    # the unit tests without touching :mod:`http.client` internals globally.
    return http.client.HTTPConnection(_HOST, _PORT, timeout=_TIMEOUT_SECONDS)


def _probe_once() -> bool:
    """Attempt a single ``GET /health`` request and return ``True`` on success."""
    connection: http.client.HTTPConnection | None = None
    try:
        connection = _create_connection()
        connection.request("GET", "/health")
        response = connection.getresponse()
        return response.status == 200
    except Exception:
        return False
    finally:
        with suppress(Exception):
            if connection is not None:
                connection.close()


def main() -> int:
    """Return ``0`` when the probe succeeds and ``1`` otherwise.

    The loop keeps the overall wait below three seconds while providing
    enough time for the API process to finish booting.  Each iteration
    closes its connection explicitly so repeated probes do not exhaust the
    server socket backlog.
    """
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        if _probe_once():
            return 0
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_DELAY_SECONDS)
    return 1


if __name__ == "__main__":
    sys.exit(main())
