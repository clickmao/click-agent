"""kvsvc HTTP 服务入口（仅标准库）。

用法:
    python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal

就绪后 stdout 打印一行 READY 并 flush。

HTTP 语义（契约）:
    PUT  /kv/{key}        {value, ttl?}      -> 200 {key,value,expires_in}
    GET  /kv/{key}                           -> 200 {key,value} | 404 not_found
    DELETE /kv/{key}                         -> 200 {deleted:true} | 404 not_found
    POST /kv/{key}/incr   {by?}              -> 200 {key,value:int} | 409 not_int
    GET  /stats                              -> 200 {count,expired,uptime_ms}
    其它                                     -> 404 {error:"not_found"}

所有响应 Content-Type: application/json; charset=utf-8，body 为 UTF-8 JSON。
并发: ThreadingHTTPServer（每请求一线程）。
"""

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .store import KVStore

JSON_CT = "application/json; charset=utf-8"

# 进程启动时间（用于 uptime_ms）
_START_TS = time.time()

# 由 main() 注入
_STORE: KVStore = None  # type: ignore


class Handler(BaseHTTPRequestHandler):
    # 使用 HTTP/1.1 以便支持 keep-alive；显式声明 length
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ---- 输出工具 ----

    def _send_json(self, status: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return data

    # ---- 路由 ----

    def _route(self):
        parsed = urlparse(self.path)
        path = parsed.path
        parts = [p for p in path.split("/") if p != ""]
        # 期望形态: kv/{key}  或  kv/{key}/incr  或  stats
        if parts == ["stats"]:
            if self.command != "GET":
                return self._send_json(404, {"error": "not_found"})
            st = _STORE.stats()
            uptime_ms = int((time.time() - _START_TS) * 1000)
            return self._send_json(200, {
                "count": st["count"],
                "expired": st["expired"],
                "uptime_ms": uptime_ms,
            })

        if len(parts) == 2 and parts[0] == "kv":
            key = unquote(parts[1])
            if self.command == "PUT":
                return self._do_put(key)
            if self.command == "GET":
                return self._do_get(key)
            if self.command == "DELETE":
                return self._do_delete(key)
            return self._send_json(404, {"error": "not_found"})

        if len(parts) == 3 and parts[0] == "kv" and parts[2] == "incr":
            key = unquote(parts[1])
            if self.command == "POST":
                return self._do_incr(key)
            return self._send_json(404, {"error": "not_found"})

        return self._send_json(404, {"error": "not_found"})

    def _do_put(self, key: str):
        data = self._read_json_body()
        if not isinstance(data, dict) or "value" not in data:
            return self._send_json(404, {"error": "not_found"})
        value = data["value"]
        ttl = data.get("ttl", None)
        if ttl is not None:
            try:
                ttl = float(ttl)
            except (TypeError, ValueError):
                ttl = None
        expires_in = _STORE.put(key, value, ttl)
        return self._send_json(200, {
            "key": key, "value": value, "expires_in": expires_in,
        })

    def _do_get(self, key: str):
        res = _STORE.get(key)
        if res is None:
            return self._send_json(404, {"error": "not_found"})
        value, _expires_in = res
        return self._send_json(200, {"key": key, "value": value})

    def _do_delete(self, key: str):
        ok = _STORE.delete(key)
        if not ok:
            return self._send_json(404, {"error": "not_found"})
        return self._send_json(200, {"deleted": True})

    def _do_incr(self, key: str):
        data = self._read_json_body()
        if data is None:
            data = {}
        if not isinstance(data, dict):
            data = {}
        by = data.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            try:
                by = int(by)
            except (TypeError, ValueError):
                by = 1
        ok, value = _STORE.incr(key, by)
        if not ok:
            return self._send_json(409, {"error": "not_int"})
        return self._send_json(200, {"key": key, "value": value})

    # ---- 钩子：避免向 stdout/stderr 打印多余文字（基线铁律）----

    def do_GET(self):
        try:
            self._route()
        except BrokenPipeError:
            pass

    def do_POST(self):
        try:
            self._route()
        except BrokenPipeError:
            pass

    def do_PUT(self):
        try:
            self._route()
        except BrokenPipeError:
            pass

    def do_DELETE(self):
        try:
            self._route()
        except BrokenPipeError:
            pass

    def log_message(self, fmt, *args):  # 静默访问日志
        pass


def main(argv=None) -> int:
    global _STORE
    ap = argparse.ArgumentParser(prog="kvsvc.server", add_help=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--wal", required=True)
    args = ap.parse_args(argv)

    _STORE = KVStore(args.wal)
    httpd = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    httpd.daemon_threads = True

    # 就绪信号：必须一行 READY 并 flush（契约 1）
    sys.stdout.write("READY\n")
    sys.stdout.flush()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        _STORE.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
