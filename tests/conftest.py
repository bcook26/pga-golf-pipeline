"""Test-suite wide settings.

The public API is rate limited in production; the existing API tests make far
more requests than a real visitor would, so the limiter is off unless a test
installs its own (see test_ratelimit.py). Set before any ``app`` import.
"""

import os

for name in (
    "RATE_LIMIT_PER_MINUTE",
    "RATE_LIMIT_PER_HOUR",
    "RATE_LIMIT_GLOBAL_PER_HOUR",
):
    os.environ[name] = "0"
