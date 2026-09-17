"""HTTP 服务层: 基于 http.server.ThreadingHTTPServer (标准库, threaded)。

启动: python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal
就绪后 stdout 打印一行 READY 并 flush。

路由
----
PUT    /kv/{key}        体 {"value":任意JSON,"ttl":数字可选(秒)}
GET    /kv/{key}
DELETE /kv/{key}
POST   /kv/{key}/incr   体 {"by":整数, 默认 1}
GET    /stats
其它路径/方法 -> 404 {"error":"not_found"}

口径说明
--------
* expires_in = 剩余秒数, 保留到毫秒 (round 到 3 位), 保证 <= 请求的 ttl
  (避免浮点表示导致 0.2 被打印成 0.200000047... 这类超出请求值的假象)。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlsplit

from .store import KVStore, _MISSING


# ---------------------------------------------------------------- 路由解析
def _parse_route(method: str, path: str) -> Tuple[str, Optional[str]]:
    """把请求解析为 (route, key)。route 取值见模块文档。"""
    parts = path.split("/")  # path 以 "/" 开头 -> parts[0] == ""
    if len(parts) >= 3 and parts[1] == "kv":
        key = unquote(parts[2])
        if method in ("PUT", "GET", "DELETE") and len(parts) == 3:
            return method.lower(), key
        if method == "POST" and len(parts) == 4 and parts[3] == "incr":
            return "incr", key
        return "not_found", None
    if method == "GET" and len(parts) == 2 and parts[1] == "stats":
        return "stats", None
    return "not_found", None


class KVHandler(BaseHTTPRequestHandler):
    server_version = "kvsvc/1.0"
    protocol_version = "HTTP/1.0"  # 每请求单连接, 兼容性最稳

    # 由 create_server 注入到子类
    store: KVStore
    started_at: float

    # ---------------------------------------------------------- 响应工具
    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Any:
        """读取并解析 JSON 体; 空体 -> {}, 解析失败 -> None。"""
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def log_message(self, fmt: str, *args: Any) -> None:  # 静默, 不污染 stdout
        pass

    # ------------------------------------------------------------- 分发
    def _dispatch(self, method: str) -> None:
        path = urlsplit(self.path).path
        route, key = _parse_route(method, path)

        if route == "not_found":
            self._send_json(404, {"error": "not_found"})
            return

        if route == "put":
            body = self._read_json()
            if not isinstance(body, dict) or "value" not in body:
                self._send_json(400, {"error": "bad_request"})
                return
            ttl = body.get("ttl")
            if ttl is not None and (
                isinstance(ttl, bool) or not isinstance(ttl, (int, float))
            ):
                self._send_json(400, {"error": "bad_request"})
                return
            remaining = self.store.put(key, body["value"], ttl)
            if remaining is not None:
                remaining = round(remaining, 3)
            self._send_json(
                200,
                {"key": key, "value": body["value"], "expires_in": remaining},
            )
            return

        if route == "get":
            value = self.store.get(key)
            if value is _MISSING:
                self._send_json(404, {"error": "not_found"})
                return
            self._send_json(200, {"key": key, "value": value})
            return

        if route == "delete":
            if self.store.delete(key):
                self._send_json(200, {"deleted": True})
            else:
                self._send_json(404, {"error": "not_found"})
            return

        if route == "incr":
            body = self._read_json()
            if not isinstance(body, dict):
                self._send_json(400, {"error": "bad_request"})
                return
            by = body.get("by", 1)
            if isinstance(by, bool) or not isinstance(by, int):
                self._send_json(400, {"error": "bad_request"})
                return
            ok, value = self.store.incr(key, by)
            if not ok:
                self._send_json(409, {"error": "not_int"})
                return
            self._send_json(200, {"key": key, "value": value})
            return

        if route == "stats":
            st = self.store.stats()
            uptime_ms = int((time.time() - self.started_at) * 1000)
            self._send_json(
                200,
                {
                    "count": st["count"],
                    "expired": st["expired"],
                    "uptime_ms": uptime_ms,
                },
            )
            return

        self._send_json(404, {"error": "not_found"})

    # --------------------------------------------------------- HTTP 动词
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._dispatch("OPTIONS")


def create_server(port: int, wal: Optional[str]) -> ThreadingHTTPServer:
    """创建 threaded HTTP 服务器, 并绑定 store/启动时刻。"""
    store = KVStore(wal)
    handler_cls = type(
        "BoundKVHandler",
        (KVHandler,),
        {"store": store, "started_at": time.time()},
    )
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
    httpd.daemon_threads = True
    return httpd


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", type=str, default=None)
    args = parser.parse_args(argv)

    httpd = create_server(args.port, args.wal)
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
