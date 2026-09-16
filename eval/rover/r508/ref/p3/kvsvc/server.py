# -*- coding: utf-8 -*-
"""R508 P3 参考解 (oracle): kvsvc 包 —— HTTP 入口 (python3 -m kvsvc.server)。"""
from __future__ import annotations
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .store import Store

_STORE = None  # type: ignore


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # 静音
        return

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parts(self):
        path = self.path.split("?", 1)[0]
        seg = [s for s in path.split("/") if s != ""]
        if len(seg) == 1 and seg[0] == "stats":
            return ("stats", None, None)
        if len(seg) >= 2 and seg[0] == "kv":
            key = seg[1]
            if len(seg) == 2:
                return ("kv", key, None)
            if len(seg) == 3 and seg[2] == "incr":
                return ("incr", key, None)
        return (None, None, None)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return None

    def do_GET(self):
        kind, key, _ = self._parts()
        if kind == "stats":
            return self._send(200, _STORE.stats())
        if kind == "kv":
            r = _STORE.get(key)
            return self._send(200, r) if r else self._send(404, {"error": "not_found"})
        return self._send(404, {"error": "not_found"})

    def do_PUT(self):
        kind, key, _ = self._parts()
        if kind != "kv":
            return self._send(404, {"error": "not_found"})
        b = self._body()
        if b is None or "value" not in b:
            return self._send(400, {"error": "bad_request"})
        ttl = b.get("ttl")
        if ttl is not None:
            try:
                ttl = float(ttl)
            except (TypeError, ValueError):
                return self._send(400, {"error": "bad_request"})
        return self._send(200, _STORE.put(key, b["value"], ttl))

    def do_DELETE(self):
        kind, key, _ = self._parts()
        if kind != "kv":
            return self._send(404, {"error": "not_found"})
        return self._send(200, {"deleted": True}) if _STORE.delete(key) else self._send(404, {"error": "not_found"})

    def do_POST(self):
        kind, key, _ = self._parts()
        if kind != "incr":
            return self._send(404, {"error": "not_found"})
        b = self._body()
        if b is None:
            return self._send(400, {"error": "bad_request"})
        by = b.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            return self._send(400, {"error": "bad_request"})
        r = _STORE.incr(key, by)
        return self._send(200, r) if r != "not_int" else self._send(409, {"error": "not_int"})


def main() -> None:
    global _STORE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--wal", required=True)
    a = ap.parse_args()
    _STORE = Store(a.wal)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    srv.daemon_threads = True
    print("READY", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
