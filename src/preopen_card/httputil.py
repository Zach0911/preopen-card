"""stdlib urllib fetch with timeout, size cap, retries, and opener injection."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = (
    "preopen-card/0.1 (+https://github.com/Zach0911/preopen-card; educational; no-key)"
)
DEFAULT_TIMEOUT_S = 8.0
MAX_BYTES = 1_500_000
MAX_ATTEMPTS = 3
RETRY_SLEEP_S = 0.4

_opener: urllib.request.OpenerDirector | None = None


class FetchError(Exception):
    """Network or parse failure that callers must degrade on."""


def set_opener(opener: urllib.request.OpenerDirector | None) -> None:
    """Tests inject a fake opener; pass None to restore the default."""
    global _opener
    _opener = opener


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if not newurl.startswith(("http://", "https://")):
            raise FetchError("redirect to non-http(s)")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _default_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_SafeRedirectHandler)


def fetch_bytes(url: str, *, timeout: float = DEFAULT_TIMEOUT_S) -> bytes:
    if os.environ.get("PREOPEN_OFFLINE") == "1":
        raise FetchError("offline")
    if not url.startswith(("http://", "https://")):
        raise FetchError("unsupported url scheme")

    last_err: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return _fetch_bytes_once(url, timeout=timeout)
        except FetchError as exc:
            msg = str(exc)
            if msg in {"offline", "unsupported url scheme"} or msg.startswith(
                "response too large"
            ):
                raise
            last_err = exc
        except Exception as exc:  # noqa: BLE001 — degrade all transport errors
            last_err = FetchError(str(exc) or exc.__class__.__name__)
        if attempt + 1 < MAX_ATTEMPTS:
            time.sleep(RETRY_SLEEP_S)
    raise FetchError(str(last_err) if last_err else "fetch failed")


def _fetch_bytes_once(url: str, *, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = _opener or _default_opener()
    try:
        resp = opener.open(req, timeout=timeout)
    except FetchError:
        raise
    except urllib.error.HTTPError as exc:
        raise FetchError(f"http {exc.code}") from exc
    except Exception as exc:  # noqa: BLE001
        raise FetchError(str(exc) or exc.__class__.__name__) from exc

    try:
        status = getattr(resp, "status", None) or getattr(resp, "code", None) or resp.getcode()
        if status is not None and not (200 <= int(status) < 300):
            raise FetchError(f"http {status}")
        final_url = resp.geturl() if hasattr(resp, "geturl") else url
        if final_url and not str(final_url).startswith(("http://", "https://")):
            raise FetchError("redirect to non-http(s)")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise FetchError("response too large")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        try:
            resp.close()
        except Exception:
            pass


def fetch_text(url: str, *, encoding: str = "utf-8") -> str:
    data = fetch_bytes(url)
    return data.decode(encoding, errors="replace")


def fetch_json(url: str) -> Any:
    text = fetch_text(url)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise FetchError("invalid json") from exc
