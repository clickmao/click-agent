"""HTTP 服务层（仅标准库）。入口: python3 -m kvsvc.server --port PORT --wal PATH

路由:
  PUT    /kv/{key}        体 {"value":任意JSON,"ttl":数字可选} -> 200 {"key","value","expires_in"}
  GET    /kv/{key}        -> 200 {"key","value"} | 404 {"error":"not_found"}
  DELETE /kv/{key}        -> 200 {"deleted":true} | 404 {"error":"not_found"}
  POST   /kv/{key}/incr   体 {"by":整数,默认1} -> 200 {"key","value"} | 409 {"error":"not_int"}
  GET    /stats           -> 200 {"count","expired","uptime_ms"}
  其它路径/方法           -> 404 {"error":"not_found"}

并发: ThreadingHTTPServer，每个请求独立线程。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from kvsvc.store import KVStore

CONTENT_TYPE = "application/json; charset=utf-8"

_STORE = None            # 进程级唯一存储实例（由 main 注入）
_STORE_LOCK = threading.Lock()


def _get_store():
    return _STORE


def _json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", CONTENT_TYPE)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_body(handler):
    """读取并解析请求体；空体视为 {}；非法 JSON 返回 None。"""
    try:
        length = int(handler.headers.get("Content-Length") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _split_path(path):
    """返回去掉前导斜杠后的路径段列表（已 URL 解码）。"""
    segments = [unquote(s) for s in urlsplit(path).path.split("/") if s != ""]
    return segments


class KvHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ---- 日志：默认 stderr 由 logging 输出，这里静默以保持 stdout 只含 READY ----
    def log_message(self, fmt, *args):
        return

    # ---------------- 路由 ----------------

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

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def _dispatch(self, method):
        store = _get_store()
        store_lock = _STORE_LOCK
        try:
            segments = _split_path(self.path)
        except Exception:
            _json_response(self, 404, {"error": "not_found"})
            return

        # GET /stats
        if method == "GET" and segments == ["stats"]:
            count, expired, uptime_ms = store.stats()
            _json_response(self, 200, {
                "count": count,
                "expired": expired,
                "uptime_ms": uptime_ms,
            })
            return

        # /kv/{key} 与 /kv/{key}/incr
        if len(segments) >= 2 and segments[0] == "kv":
            key = segments[1]
            if len(segments) == 2 and method == "PUT":
                self._handle_put(store, store_lock, key)
                return
            if len(segments) == 2 and method == "GET":
                self._handle_get(store, store_lock, key)
                return
            if len(segments) == 2 and method == "DELETE":
                self._handle_delete(store, store_lock, key)
                return
            if len(segments) == 3 and segments[2] == "incr" and method == "POST":
                self._handle_incr(store, store_lock, key)
                return

        _json_response(self, 404, {"error": "not_found"})

    # ---------------- 各路由处理 ----------------

    def _handle_put(self, store, store_lock, key):
        body = _read_body(self)
        if body is None or not isinstance(body, dict):
            _json_response(self, 400, {"error": "bad_request"})
            return
        value = body.get("value")
        ttl = body.get("ttl")
        if ttl is not None:
            if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                _json_response(self, 400, {"error": "bad_request"})
                return
            ttl = float(ttl)
            if ttl < 0:
                ttl = 0.0
        expire_at = store.put(key, value, ttl=ttl)
        if expire_at is None:
            expires_in = None
        else:
            expires_in = max(0.0, expire_at - time.time())
        _json_response(self, 200, {
            "key": key,
            "value": value,
            "expires_in": expires_in,
        })

    def _handle_get(self, store, store_lock, key):
        found, value = store.get(key)
        if not found:
            _json_response(self, 404, {"error": "not_found"})
            return
        _json_response(self, 200, {"key": key, "value": value})

    def _handle_delete(self, store, store_lock, key):
        if store.delete(key):
            _json_response(self, 200, {"deleted": True})
        else:
            _json_response(self, 404, {"error": "not_found"})

    def _handle_incr(self, store, store_lock, key):
        body = _read_body(self)
        if body is None or not isinstance(body, dict):
            _json_response(self, 400, {"error": "bad_request"})
            return
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            _json_response(self, 400, {"error": "bad_request"})
            return
        status, value = store.incr(key, by)
        if status == "not_int":
            _json_response(self, 409, {"error": "not_int"})
            return
        _json_response(self, 200, {"key": key, "value": value})


def build_server(port, wal_path, host="0.0.0.0"):
    """构造（但不启动）服务实例，便于测试复用。"""
    global _STORE
    _STORE = KVStore(wal_path)
    server = ThreadingHTTPServer((host, port), KvHandler)
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m kvsvc.server")
    parser.add_argument("--port", type=int, required=True, help="监听端口")
    parser.add_argument("--wal", type=str, required=True, help="WAL 文件路径")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")
    args = parser.parse_args(argv)

    server = build_server(args.port, args.wal, args.host)
    # 就绪信号：stdout 打印一行 READY 并 flush。
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
