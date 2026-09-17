"""HTTP 服务入口：python3 -m kvsvc.server --port {int} --wal {path}

仅用标准库 http.server（ThreadingHTTPServer 天然多线程）。
就绪后在 stdout 打印一行 READY 并 flush。
"""

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from kvsvc.store import KVStore, NotInt

_CT = "application/json; charset=utf-8"
_STORE = None  # 进程级单例，由 main() 装配


def _json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---- 基础工具 ----

    def _send(self, code, obj):
        body = _json_bytes(obj)
        self.send_response(code)
        self.send_header("Content-Type", _CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self):
        self._send(404, {"error": "not_found"})

    def _read_json_body(self):
        """读取请求体并解析 JSON；空体返回 {}；非法 JSON 返回 None。"""
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            n = int(length)
        except ValueError:
            return None
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def log_message(self, fmt, *args):  # 安静模式：不污染 stdout
        pass

    # ---- 路由 ----

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        parts = [p for p in path.split("/") if p != ""]  # /kv/{key}

        if method == "GET" and path == "/stats":
            self._send(200, _STORE.stats())
            return

        # /kv/{key} 与 /kv/{key}/incr
        if len(parts) == 2 and parts[0] == "kv":
            key = unquote(parts[1])
            if method == "PUT":
                self._handle_put(key)
                return
            if method == "GET":
                self._handle_get(key)
                return
            if method == "DELETE":
                self._handle_delete(key)
                return
            self._not_found()
            return

        if len(parts) == 3 and parts[0] == "kv" and parts[2] == "incr":
            key = unquote(parts[1])
            if method == "POST":
                self._handle_incr(key)
                return
            self._not_found()
            return

        self._not_found()

    # ---- 各动作 ----

    def _handle_put(self, key):
        body = self._read_json_body()
        if body is None or not isinstance(body, dict) or "value" not in body:
            self._not_found()
            return
        ttl = body.get("ttl", None)
        if ttl is not None:
            if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                self._not_found()
                return
        result = _STORE.put(key, body["value"], ttl)
        self._send(200, result)

    def _handle_get(self, key):
        result = _STORE.get(key)
        if result is None:
            self._not_found()
            return
        self._send(200, result)

    def _handle_delete(self, key):
        if not _STORE.delete(key):
            self._not_found()
            return
        self._send(200, {"deleted": True})

    def _handle_incr(self, key):
        body = self._read_json_body()
        if body is None:
            self._not_found()
            return
        by = body.get("by", 1) if isinstance(body, dict) else 1
        if isinstance(by, bool) or not isinstance(by, int):
            self._not_found()
            return
        try:
            result = _STORE.incr(key, by)
        except NotInt:
            self._send(409, {"error": "not_int"})
            return
        self._send(200, result)

    # HTTP 方法入口

    def do_GET(self):
        self._dispatch("GET")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_POST(self):
        self._dispatch("POST")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", type=str, required=True)
    args = parser.parse_args(argv)

    global _STORE
    _STORE = KVStore(wal_path=args.wal)
    _STORE.replay_wal()  # 启动时从 WAL 恢复

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print("READY", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        _STORE.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
