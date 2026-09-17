"""HTTP entry point: python3 -m kvsvc.server --port PORT --wal PATH"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional, Tuple
from urllib.parse import unquote, urlparse

from .store import KVStore

_JSON_CT = "application/json; charset=utf-8"
_KEY_RE = re.compile(r"^/kv/([^/]+)$")
_INCR_RE = re.compile(r"^/kv/([^/]+)/incr$")


class Api:
    def __init__(self, store: KVStore) -> None:
        self.store = store
        self.started = time.time()

    def uptime_ms(self) -> int:
        return int((time.time() - self.started) * 1000)


def _parse_body(handler: BaseHTTPRequestHandler) -> Tuple[Optional[Any], bool]:
    """Read and decode a JSON body. Returns (data, ok)."""
    length = handler.headers.get("Content-Length")
    raw = b""
    if length:
        try:
            n = int(length)
        except ValueError:
            n = 0
        if n > 0:
            raw = handler.rfile.read(n)
    if not raw:
        return {}, True
    try:
        return json.loads(raw.decode("utf-8")), True
    except (ValueError, UnicodeDecodeError):
        return None, False


def _path_key(path: str) -> Optional[str]:
    m = _KEY_RE.match(path)
    if not m:
        return None
    return unquote(m.group(1))


def _ttl_of(body: Any) -> Tuple[Optional[float], bool]:
    if not isinstance(body, dict):
        return None, True
    if "ttl" not in body or body["ttl"] is None:
        return None, True
    ttl = body["ttl"]
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
        return None, False
    return float(ttl), True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # -- plumbing ----------------------------------------------------------
    def log_message(self, fmt: str, *args: Any) -> None:  # keep stderr quiet
        pass

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", _JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send(404, {"error": "not_found"})

    def _method_not_allowed(self) -> None:
        self._not_found()

    # -- verbs -------------------------------------------------------------
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/stats":
            stats = self.server.api.store.stats()
            self._send(
                200,
                {
                    "count": stats["count"],
                    "expired": stats["expired"],
                    "uptime_ms": self.server.api.uptime_ms(),
                },
            )
            return
        key = _path_key(path)
        if key is None:
            self._not_found()
            return
        value = self.server.api.store.get(key)
        if value is None:
            self._not_found()
            return
        self._send(200, {"key": key, "value": value})

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        key = _path_key(path)
        if key is None:
            self._not_found()
            return
        body, ok = _parse_body(self)
        if not ok or not isinstance(body, dict) or "value" not in body:
            self._send(400, {"error": "bad_request"})
            return
        ttl, ttl_ok = _ttl_of(body)
        if not ttl_ok:
            self._send(400, {"error": "bad_request"})
            return
        resp = self.server.api.store.put(key, body["value"], ttl)
        self._send(200, resp)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        key = _path_key(path)
        if key is None:
            self._not_found()
            return
        # Drain any body so keep-alive clients stay in sync.
        if self.headers.get("Content-Length"):
            try:
                n = int(self.headers["Content-Length"])
            except ValueError:
                n = 0
            if n > 0:
                self.rfile.read(n)
        if not self.server.api.store.delete(key):
            self._not_found()
            return
        self._send(200, {"deleted": True})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        m = _INCR_RE.match(path)
        if not m:
            self._not_found()
            return
        key = unquote(m.group(1))
        body, ok = _parse_body(self)
        if not ok:
            self._send(400, {"error": "bad_request"})
            return
        if body is None:
            body = {}
        if not isinstance(body, dict):
            self._send(400, {"error": "bad_request"})
            return
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            self._send(400, {"error": "bad_request"})
            return
        result = self.server.api.store.incr(key, by)
        if not result["ok"]:
            self._send(409, {"error": "not_int"})
            return
        self._send(200, {"key": key, "value": result["value"]})

    # Any other method -> 404 not_found
    def do_PATCH(self) -> None:
        self._method_not_allowed()

    def do_HEAD(self) -> None:
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:
        self._method_not_allowed()

    def do_TRACE(self) -> None:
        self._method_not_allowed()

    def do_CONNECT(self) -> None:
        self._method_not_allowed()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: Tuple[str, int], store: KVStore) -> None:
        super().__init__(addr, Handler)
        self.api = Api(store)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", required=True)
    args = parser.parse_args(argv)

    store = KVStore(args.wal)
    server = Server(("0.0.0.0", args.port), store)
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
