from __future__ import annotations

import io
from urllib.error import HTTPError

import pytest

from preopen_card import httputil


class _Resp(io.BytesIO):
    def __init__(self, data: bytes, status: int = 200, url: str = "https://example.com/x"):
        super().__init__(data)
        self.status = status
        self.code = status
        self._url = url

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url


class _Opener:
    def __init__(self, resp=None, exc=None):
        self.resp = resp
        self.exc = exc
        self.calls = 0

    def open(self, req, timeout=None):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.resp


@pytest.fixture(autouse=True)
def _reset_opener():
    httputil.set_opener(None)
    yield
    httputil.set_opener(None)


def test_offline_env(monkeypatch):
    monkeypatch.setenv("PREOPEN_OFFLINE", "1")
    with pytest.raises(httputil.FetchError, match="offline"):
        httputil.fetch_bytes("https://example.com")


def test_rejects_non_http(monkeypatch):
    monkeypatch.delenv("PREOPEN_OFFLINE", raising=False)
    with pytest.raises(httputil.FetchError, match="unsupported"):
        httputil.fetch_bytes("file:///etc/passwd")


def test_non_200(monkeypatch):
    monkeypatch.delenv("PREOPEN_OFFLINE", raising=False)
    err = HTTPError("https://example.com", 503, "nope", hdrs=None, fp=io.BytesIO())
    opener = _Opener(exc=err)
    httputil.set_opener(opener)
    monkeypatch.setattr(httputil, "RETRY_SLEEP_S", 0)
    with pytest.raises(httputil.FetchError, match="http 503"):
        httputil.fetch_bytes("https://example.com")
    assert opener.calls == httputil.MAX_ATTEMPTS


def test_too_large(monkeypatch):
    monkeypatch.delenv("PREOPEN_OFFLINE", raising=False)
    blob = b"x" * (httputil.MAX_BYTES + 10)
    httputil.set_opener(_Opener(resp=_Resp(blob)))
    with pytest.raises(httputil.FetchError, match="too large"):
        httputil.fetch_bytes("https://example.com")


def test_ok_json(monkeypatch):
    monkeypatch.delenv("PREOPEN_OFFLINE", raising=False)
    httputil.set_opener(_Opener(resp=_Resp(b'{"ok": true}')))
    assert httputil.fetch_json("https://example.com") == {"ok": True}


def test_invalid_json(monkeypatch):
    monkeypatch.delenv("PREOPEN_OFFLINE", raising=False)
    httputil.set_opener(_Opener(resp=_Resp(b"not-json")))
    with pytest.raises(httputil.FetchError, match="invalid json"):
        httputil.fetch_json("https://example.com")
