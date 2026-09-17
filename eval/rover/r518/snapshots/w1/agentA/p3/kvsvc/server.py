"""HTTP 服务入口（仅标准库，不联网）。

用法:
    python3 -m kvsvc.server --port 8080 --wal /abs/path/wal.jsonl

* 就绪后 stdout 打印一行 ``READY`` 并 flush（此后不再打印任何多余文字）。
* 所有响应 body 为 UTF-8 JSON，Content-Type 恒为
  ``application/json; charset=utf-8``。
* 并发模型: ThreadingHTTPServer（每请求一线程），存储内核自带锁。
* 路由:
    PUT    /kv/{key}        {"value":任意JSON,"ttl":数字可选}
    GET    /kv/{key}
    DELETE /kv/{key}
    POST   /kv/{key}/incr   {"by":整数,默认1}
    GET    /stats
  其它路径/方法一律 404 {"error":"not_found"}。
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .store import KVStore

_CONTENT_TYPE = "application/json; charset=utf-8"


class KVRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store = None  # 由 main() 注入

    # ---------------- 基础工具 ----------------

    def log_message(self, fmt, *args):
        """静默日志：stdout 只允许出现 READY。"""
        return

    def _send_json(self, code, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", _CONTENT_TYPE)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _not_found(self):
        self._send_json(404, {"error": "not_found"})

    def _read_body(self):
        """读满 Content-Length 字节再解析；返回 {} / dict / None(非法 JSON)。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _segments(self):
        """拆路径为段并做百分号解码（key 可含 URL 编码字符）。"""
        path = urlparse(self.path).path
        return [unquote(seg) for seg in path.split("/") if seg != ""]

    # ---------------- 路由 ----------------

    def do_GET(self):
        self._read_body()  # 排空请求体，保持 keep-alive 帧对齐
        segs = self._segments()
        if segs == ["stats"]:
            self._send_json(200, self.store.stats())
            return
        if len(segs) == 2 and segs[0] == "kv":
            got = self.store.get(segs[1])
            if got is None:
                self._not_found()
            else:
                self._send_json(200, got)
            return
        self._not_found()

    def do_PUT(self):
        segs = self._segments()
        body = self._read_body()
        if not (len(segs) == 2 and segs[0] == "kv"):
            self._not_found()
            return
        if not isinstance(body, dict):
            self._send_json(400, {"error": "bad_request"})
            return
        ttl = body.get("ttl")
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, (int, float))):
            self._send_json(400, {"error": "bad_request"})
            return
        self._send_json(200, self.store.put(segs[1], body.get("value"), ttl))

    def do_DELETE(self):
        segs = self._segments()
        body = self._read_body()
        if len(segs) == 2 and segs[0] == "kv":
            if self.store.delete(segs[1]):
                self._send_json(200, {"deleted": True})
            else:
                self._not_found()
            return
        self._not_found()

    def do_POST(self):
        segs = self._segments()
        body = self._read_body()
        if len(segs) == 3 and segs[0] == "kv" and segs[2] == "incr":
            if not isinstance(body, dict):
                self._send_json(400, {"error": "bad_request"})
                return
            by = body.get("by", 1)
            if isinstance(by, bool) or not isinstance(by, int):
                self._send_json(400, {"error": "bad_request"})
                return
            status, value = self.store.incr(segs[1], by)
            if status == "not_int":
                self._send_json(409, {"error": "not_int"})
            else:
                self._send_json(200, {"key": segs[1], "value": value})
            return
        self._not_found()

    def __getattr__(self, name):
        """未显式实现的 HTTP 方法（PATCH/OPTIONS/...）一律 404 not_found。"""
        if name.startswith("do_"):
            return self._unknown_method
        raise AttributeError(name)

    def _unknown_method(self):
        self._read_body()
        self._not_found()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    store = KVStore(args.wal)
    KVRequestHandler.store = store

    httpd = ThreadingHTTPServer((args.host, args.port), KVRequestHandler)
    httpd.daemon_threads = True

    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        store.close()


if __name__ == "__main__":
    main()
