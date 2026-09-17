"""kvsvc HTTP 服务入口。

运行:
    python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal

就绪后 stdout 打印一行 ``READY`` 并 flush。

所有响应 Content-Type 固定为 ``application/json; charset=utf-8``,
body 为 UTF-8 JSON。并发由 ``ThreadingHTTPServer``(每连接一线程)保证。
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlsplit

from .store import KvStore, NotIntError

# 进程级单例, 由 build_server() 注入; 供 handler 访问。
_STORE: Optional[KvStore] = None


class KvHandler(BaseHTTPRequestHandler):
    """KV 路由处理器; 由 ``ThreadingHTTPServer`` 为每个连接起一个线程。"""

    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ------------------------------------------------------------------ #
    # 基础工具
    # ------------------------------------------------------------------ #
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        """访问日志写 stderr, 避免污染 stdout 的 READY 契约。"""
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(404, {"error": "not_found"})

    def _read_body(self) -> Optional[Dict[str, Any]]:
        """读取请求体并解析为 JSON 对象; 失败返回 None。"""
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return None
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    @staticmethod
    def _split_path(path: str) -> Tuple[str, Optional[str]]:
        """把路径拆成 (kind, key); kind ∈ {kv, incr, stats, other}。"""
        parts = [p for p in urlsplit(path).path.split("/") if p != ""]
        if not parts:
            return ("other", None)
        if parts[0] == "kv" and len(parts) == 2:
            return ("kv", unquote(parts[1]))
        if parts[0] == "kv" and len(parts) == 3 and parts[2] == "incr":
            return ("incr", unquote(parts[1]))
        if parts[0] == "stats" and len(parts) == 1:
            return ("stats", None)
        return ("other", None)

    # ------------------------------------------------------------------ #
    # HTTP 方法
    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:  # noqa: N802
        kind, key = self._split_path(self.path)
        if kind == "stats":
            st = _STORE.stats()
            self._send_json(
                200,
                {
                    "count": st["count"],
                    "expired": st["expired"],
                    "uptime_ms": _STORE.uptime_ms(),
                },
            )
            return
        if kind == "kv":
            if not _STORE.has(key):
                self._not_found()
                return
            self._send_json(200, {"key": key, "value": _STORE.get(key)})
            return
        self._not_found()

    def do_PUT(self) -> None:  # noqa: N802
        kind, key = self._split_path(self.path)
        if kind != "kv":
            self._not_found()
            return
        body = self._read_body()
        if body is None or "value" not in body:
            self._not_found()
            return
        ttl = body.get("ttl")
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, (int, float))):
            self._not_found()
            return
        try:
            _STORE.put(key, body["value"], None if ttl is None else float(ttl))
        except (TypeError, ValueError):
            self._not_found()
            return
        self._send_json(
            200,
            {
                "key": key,
                "value": body["value"],
                "expires_in": _STORE.expires_in(key),
            },
        )

    def do_DELETE(self) -> None:  # noqa: N802
        kind, key = self._split_path(self.path)
        if kind != "kv" or not _STORE.delete(key):
            self._not_found()
            return
        self._send_json(200, {"deleted": True})

    def do_POST(self) -> None:  # noqa: N802
        kind, key = self._split_path(self.path)
        if kind != "incr":
            self._not_found()
            return
        body = self._read_body()
        if body is None:
            self._not_found()
            return
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            self._not_found()
            return
        try:
            value = _STORE.incr(key, by)
        except NotIntError:
            self._send_json(409, {"error": "not_int"})
            return
        self._send_json(200, {"key": key, "value": value})

    # 未实现的其它方法统一走 404。
    def do_HEAD(self) -> None:  # noqa: N802
        self._not_found()

    def do_PATCH(self) -> None:  # noqa: N802
        self._not_found()


def build_server(
    port: int, wal: Optional[str], bind: str = "127.0.0.1"
) -> ThreadingHTTPServer:
    """创建(不启动)服务实例; 供自检与外部嵌入复用。"""
    global _STORE  # noqa: PLW0603
    _STORE = KvStore(wal_path=wal)
    return ThreadingHTTPServer((bind, port), KvHandler)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kvsvc.server", description="带 TTL 的 KV 服务")
    parser.add_argument("--port", type=int, required=True, help="监听端口")
    parser.add_argument("--wal", type=str, default=None, help="WAL 文件路径")
    parser.add_argument("--bind", type=str, default="127.0.0.1", help="监听地址")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    server = build_server(args.port, args.wal, args.bind)
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
