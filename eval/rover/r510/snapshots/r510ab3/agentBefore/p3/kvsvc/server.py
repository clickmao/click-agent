"""HTTP 服务入口: python3 -m kvsvc.server --port {int} --wal {path}

路由概览见 README。所有响应 Content-Type = application/json; charset=utf-8。
使用 ThreadingHTTPServer 支持并发请求。
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .store import KVStore

_JSON_CT = "application/json; charset=utf-8"

# 由 main() 设置，供 handler 访问
_STORE: KVStore = None  # type: ignore[assignment]


def _split(path: str):
    """解析 /kv/{key} 与 /kv/{key}/incr 与 /stats。返回 (name, key, action) 或 None。"""
    p = path
    if not p.startswith("/"):
        return None
    parts = [seg for seg in p.split("/") if seg != ""]
    if len(parts) == 1 and parts[0] == "stats":
        return ("stats", None, None)
    if parts and parts[0] == "kv":
        if len(parts) == 2:
            return ("kv", unquote(parts[1]), None)
        if len(parts) == 3 and parts[2] == "incr":
            return ("kv", unquote(parts[1]), "incr")
    return None


class KVHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"
    # 静默: 不打印任何日志(遵守“不要打印多余文字”)
    def log_message(self, fmt, *args):  # noqa: N802
        return

    # ---- 工具 ----

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", _JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            n = int(length)
        except (TypeError, ValueError):
            return {}
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None  # 标记非法 JSON

    # ---- HTTP 方法 ----

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        route = _split(path)
        if route is None:
            return self._send(404, {"error": "not_found"})
        name, key, action = route
        if name == "stats":
            return self._send(200, _STORE.stats())
        if name == "kv":
            got = _STORE.get(key)
            if got is None:
                return self._send(404, {"error": "not_found"})
            value, _expires_in = got
            return self._send(200, {"key": key, "value": value})
        return self._send(404, {"error": "not_found"})

    def do_PUT(self):  # noqa: N802
        path = urlparse(self.path).path
        route = _split(path)
        if route is None or route[0] != "kv" or route[2] is not None:
            return self._send(404, {"error": "not_found"})
        _, key, _ = route
        body = self._read_json()
        if not isinstance(body, dict) or "value" not in body:
            return self._send(400, {"error": "bad_request"})
        ttl = body.get("ttl")
        try:
            expires_in = _STORE.put(key, body["value"], ttl)
        except TypeError:
            return self._send(400, {"error": "bad_request"})
        return self._send(200, {"key": key, "value": body["value"], "expires_in": expires_in})

    def do_DELETE(self):  # noqa: N802
        path = urlparse(self.path).path
        route = _split(path)
        if route is None or route[0] != "kv" or route[2] is not None:
            return self._send(404, {"error": "not_found"})
        _, key, _ = route
        if _STORE.delete(key):
            return self._send(200, {"deleted": True})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        route = _split(path)
        if route is None or route[0] != "kv" or route[2] != "incr":
            return self._send(404, {"error": "not_found"})
        _, key, _ = route
        body = self._read_json()
        if body is None:
            return self._send(400, {"error": "bad_request"})
        by = body.get("by", 1) if isinstance(body, dict) else 1
        try:
            ok, val = _STORE.incr(key, by)
        except TypeError:
            return self._send(400, {"error": "bad_request"})
        if not ok:
            return self._send(409, {"error": "not_int"})
        return self._send(200, {"key": key, "value": val})


def build_server(port: int, wal: str) -> ThreadingHTTPServer:
    global _STORE
    _STORE = KVStore(wal_path=wal)
    httpd = ThreadingHTTPServer(("0.0.0.0", port), KVHandler)
    httpd.daemon_threads = True
    return httpd


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", type=str, required=True)
    args = parser.parse_args(argv)

    httpd = build_server(args.port, args.wal)

    def _shutdown(signum, frame):  # pragma: no cover
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    try:
        import signal

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)
    except (ImportError, ValueError):  # pragma: no cover
        pass

    # 就绪后打印一行 READY 并 flush
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        if _STORE is not None:
            _STORE.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
