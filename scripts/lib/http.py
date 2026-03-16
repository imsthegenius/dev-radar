"""HTTP utilities for dev-radar (stdlib only)."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

DEFAULT_TIMEOUT = 30
DEBUG = os.environ.get("DEV_RADAR_DEBUG", "").lower() in ("1", "true", "yes")


def log(msg: str):
    if DEBUG:
        sys.stderr.write(f"[dev-radar] {msg}\n")
        sys.stderr.flush()


MAX_RETRIES = 3
RETRY_DELAY = 2.0
USER_AGENT = "dev-radar/0.1.0"


class HTTPError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = MAX_RETRIES,
) -> str:
    """Make an HTTP request and return the response body as a string."""
    headers = headers or {}
    headers.setdefault("User-Agent", USER_AGENT)

    req = urllib.request.Request(url, headers=headers, method=method)
    log(f"{method} {url}")

    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                log(f"Response: {response.status} ({len(body)} bytes)")
                return body
        except urllib.error.HTTPError as e:
            body = None
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            log(f"HTTP Error {e.code}: {e.reason}")
            last_error = HTTPError(f"HTTP {e.code}: {e.reason}", e.code, body)
            if 400 <= e.code < 500 and e.code != 429:
                raise last_error
            if attempt < retries - 1:
                delay = RETRY_DELAY * (2 ** attempt) + (1 if e.code == 429 else 0)
                time.sleep(delay)
        except urllib.error.URLError as e:
            log(f"URL Error: {e.reason}")
            last_error = HTTPError(f"URL Error: {e.reason}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except (OSError, TimeoutError, ConnectionResetError) as e:
            log(f"Connection error: {type(e).__name__}: {e}")
            last_error = HTTPError(f"Connection error: {type(e).__name__}: {e}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))

    if last_error:
        raise last_error
    raise HTTPError("Request failed with no error details")


def get(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> str:
    return request("GET", url, headers=headers, **kwargs)


def get_json(url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
    body = get(url, headers=headers, **kwargs)
    return json.loads(body)
