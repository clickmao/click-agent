"""HTTP 服务层: 路由 + 线程化处理 + 契约化 JSON 响应。

入口:
    python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal
    python3 -m kvsvc.server --selftest        # 无头端到端自检, PASS/FAIL, 退出码 0=通过

契约
----
* 所有响应 Content-Type: application/json; charset=utf-8, body 为 UTF-8 JSON。
* PUT  /kv/{key}        {"value":任意,"ttl":数字可选} -> 200 {"key","value","expires_in"}
* GET  /kv/{key}        -> 200 {"key","value"} | 404 {"error":"not_found"}
* DELETE /kv/{key}      -> 200 {"deleted":true} | 404 {"error":"not_found"}
* POST /kv/{key}/incr   {"by":整数} -> 200 {"key","value"} | 409 {"error":"not_int"}
* GET  /stats           -> 200 {"count","expired","uptime_ms"}
* 其它路径/方法          -> 404 {"error":"not_found"}

并发模型: ThreadingHTTPServer, 每个请求一个线程; 共享的 KVStore 内部加锁。
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from .store import KVStore

_METHODS = {"PUT", "GET", "DELETE", "POST"}


def _split_path(path: str):
    """把 /kv/{key}[/incr] 解析为 (op, key)。返回 (None, None) 表示非法路径。"""
    if not path.startswith("/"):
        return None, None
    parts = [unquote(p) for p in path.split("/") if p != ""]
    if len(parts) == 2 and parts[0] == "kv":
        return "kv", parts[1]
    if len(parts) == 3 and parts[0] == "kv" and parts[2] == "incr":
        return "incr", parts[1]
    return None, None


class KVHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # 引用由 build_server 注入
    store: KVStore = None  # type: ignore[assignment]

    # -------------------------------------------------------------- 工具

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Any:
        """读取并解析请求体; 空体返回 {}。解析失败抛 ValueError。"""
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw.strip():
            return {}
        return json.loads(raw.decode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:  # 静默访问日志
        pass

    # -------------------------------------------------------------- 路由

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/stats":
            if method == "GET":
                self._send_json(200, self.store.stats())
            else:
                self._send_json(404, {"error": "not_found"})
            return

        kind, key = _split_path(path)
        if kind is None or key is None or key == "":
            self._send_json(404, {"error": "not_found"})
            return

        if method == "GET" and kind == "kv":
            res = self.store.get(key)
            if not res["found"]:
                self._send_json(404, {"error": "not_found"})
            else:
                self._send_json(200, {"key": key, "value": res["value"]})
            return

        if method == "DELETE" and kind == "kv":
            res = self.store.delete(key)
            if not res["deleted"]:
                self._send_json(404, {"error": "not_found"})
            else:
                self._send_json(200, {"deleted": True})
            return

        if method == "PUT" and kind == "kv":
            try:
                body = self._read_json_body()
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, {"error": "bad_request"})
                return
            if not isinstance(body, dict) or "value" not in body:
                self._send_json(400, {"error": "bad_request"})
                return
            ttl = body.get("ttl", None)
            if ttl is not None:
                if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                    self._send_json(400, {"error": "bad_request"})
                    return
                ttl = float(ttl)
                if ttl < 0:
                    ttl = 0.0
            try:
                res = self.store.put(key, body["value"], ttl=ttl)
            except Exception:  # value 无法序列化(不应发生, JSON 已解析)
                self._send_json(400, {"error": "bad_request"})
                return
            self._send_json(200, res)
            return

        if method == "POST" and kind == "incr":
            try:
                body = self._read_json_body()
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, {"error": "bad_request"})
                return
            by = body.get("by", 1) if isinstance(body, dict) else 1
            if isinstance(by, bool) or not isinstance(by, int):
                self._send_json(400, {"error": "bad_request"})
                return
            res = self.store.incr(key, by)
            if res["not_int"]:
                self._send_json(409, {"error": "not_int"})
            else:
                self._send_json(200, {"key": key, "value": res["value"]})
            return

        self._send_json(404, {"error": "not_found"})

    def do_GET(self) -> None:      self._dispatch("GET")
    def do_PUT(self) -> None:      self._dispatch("PUT")
    def do_DELETE(self) -> None:   self._dispatch("DELETE")
    def do_POST(self) -> None:     self._dispatch("POST")
    def do_HEAD(self) -> None:     self._dispatch("HEAD")


def build_server(host: str, port: int, wal_path: str) -> ThreadingHTTPServer:
    handler = type("BoundKVHandler", (KVHandler,), {"store": KVStore(wal_path=wal_path)})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    return httpd


def serve(host: str, port: int, wal_path: str) -> None:
    httpd = build_server(host, port, wal_path)
    actual_port = httpd.server_address[1]
    sys.stdout.write("READY %d\n" % actual_port)
    sys.stdout.flush()
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


# ------------------------------------------------------------------ 自检

def _selftest() -> int:
    """无头端到端自检: 真起服务、真发 HTTP、真并发、真重启重放。"""
    import os
    import tempfile
    import threading as _th

    failures = []

    fd, wal = tempfile.mkstemp(suffix=".wal")
    os.close(fd)
    os.remove(wal)

    dummy = ThreadingHTTPServer(("127.0.0.1", 0), KVHandler)
    port = dummy.server_address[1]
    dummy.server_close()

    srv = build_server("127.0.0.1", port, wal)
    base = "http://127.0.0.1:%d" % port
    th = _th.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    th.start()

    def req(method, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        r = urllib.request.Request(base + path, data=data, method=method)
        if data is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                ctype = resp.headers.get("Content-Type")
                return resp.status, json.loads(resp.read().decode("utf-8")), ctype
        except urllib.error.HTTPError as e:
            ctype = e.headers.get("Content-Type")
            return e.code, json.loads(e.read().decode("utf-8")), ctype

    try:
        # 契约 2: Content-Type
        st, body, ctype = req("PUT", "/kv/a", {"value": {"x": 1}})
        if ctype != "application/json; charset=utf-8":
            failures.append("Content-Type 错误: %r" % ctype)
        if st != 200 or body["value"] != {"x": 1} or body["expires_in"] is not None:
            failures.append("PUT 响应不合契约: %s %s" % (st, body))

        # GET 命中 / 未命中
        st, body, _ = req("GET", "/kv/a")
        if st != 200 or body != {"key": "a", "value": {"x": 1}}:
            failures.append("GET 命中响应错误: %s %s" % (st, body))
        st, body, _ = req("GET", "/kv/none")
        if st != 404 or body != {"error": "not_found"}:
            failures.append("GET 未命中应 404: %s %s" % (st, body))

        # TTL 到期不可见 + expired 计数
        st, _, _ = req("PUT", "/kv/t", {"value": 1, "ttl": 0.3})
        if st != 200:
            failures.append("PUT ttl 失败")
        time.sleep(0.45)
        st, body, _ = req("GET", "/kv/t")
        if st != 404:
            failures.append("TTL 到期后 GET 应 404, 实得 %s" % st)
        st, body, _ = req("GET", "/stats")
        if body.get("expired", 0) < 1:
            failures.append("expired 累计未增加: %s" % body)
        if not isinstance(body.get("uptime_ms"), int) or body["uptime_ms"] < 0:
            failures.append("uptime_ms 非法: %s" % body)
        if not isinstance(body.get("count"), int):
            failures.append("count 非法: %s" % body)

        # DELETE
        req("PUT", "/kv/d", {"value": 1})
        st, body, _ = req("DELETE", "/kv/d")
        if st != 200 or body != {"deleted": True}:
            failures.append("DELETE 响应错误: %s %s" % (st, body))
        st, body, _ = req("DELETE", "/kv/d")
        if st != 404 or body != {"error": "not_found"}:
            failures.append("DELETE 不存在应 404: %s %s" % (st, body))

        # incr: 缺省按 0 起算; 非整数 -> 409
        st, body, _ = req("POST", "/kv/c", {})
        if st != 200 or body != {"key": "c", "value": 1}:
            failures.append("incr 缺省响应错误: %s %s" % (st, body))
        req("PUT", "/kv/s", {"value": "hi"})
        st, body, _ = req("POST", "/kv/s/incr", {"by": 1})
        if st != 409 or body != {"error": "not_int"}:
            failures.append("incr 非整数应 409: %s %s" % (st, body))

        # 契约 5: 8 客户端 x 20 次 incr 恰好等于总增量
        total = 8 * 20
        errs = []
        def worker(_i):
            try:
                for _ in range(20):
                    s, _b, _c = req("POST", "/kv/cc/incr", {"by": 1})
                    if s != 200:
                        errs.append(s)
            except Exception as exc:  # noqa: BLE001
                errs.append(repr(exc))
        ws = [_th.Thread(target=worker, args=(i,)) for i in range(8)]
        for w in ws:
            w.start()
        for w in ws:
            w.join()
        st, body, _ = req("GET", "/kv/cc")
        if body.get("value") != total:
            failures.append("并发 incr 计数 %s != %s (errs=%s)" % (body.get("value"), total, errs[:3]))
        if errs:
            failures.append("并发请求出现错误: %s" % errs[:3])

        # 非法路径 / 方法
        st, body, _ = req("GET", "/nope")
        if st != 404 or body != {"error": "not_found"}:
            failures.append("未知路径应 404: %s %s" % (st, body))
        st, body, _ = req("POST", "/stats", {})
        if st != 404 or body != {"error": "not_found"}:
            failures.append("错误方法应 404: %s %s" % (st, body))

        # 契约 6: WAL 行含 op/key; 重启后重放恢复
        with open(wal, "r", encoding="utf-8") as fh:
            rows = [json.loads(x) for x in fh if x.strip()]
        if not rows:
            failures.append("WAL 为空")
        for r in rows:
            if r.get("op") not in ("put", "delete", "incr") or "key" not in r:
                failures.append("WAL 行不合契约: %s" % r)
                break

        tl = threading.Lock()
        snap = {}
        with tl:
            pass
    finally:
        srv.shutdown()
        srv.server_close()

    # 重启: 新进程等价物 —— 同一 WAL 重新构建
    srv2 = build_server("127.0.0.1", port, wal)
    base2 = "http://127.0.0.1:%d" % port
    th2 = _th.Thread(target=srv2.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    th2.start()

    def req2(method, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        r = urllib.request.Request(base2 + path, data=data, method=method)
        if data is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    try:
        st, body = req2("GET", "/kv/a")
        if st != 200 or body.get("value") != {"x": 1}:
            failures.append("重启后未恢复 put 键: %s %s" % (st, body))
        st, body = req2("GET", "/kv/cc")
        if st != 200 or body.get("value") != total:
            failures.append("重启后 incr 累计值错误: %s %s" % (st, body))
        st, body = req2("GET", "/kv/d")
        if st != 404:
            failures.append("重启后已删除键复活")
    finally:
        srv2.shutdown()
        srv2.server_close()
        for p in (wal,):
            if os.path.exists(p):
                os.remove(p)

    if failures:
        sys.stderr.write("FAIL\n")
        for f in failures:
            sys.stderr.write("  - %s\n" % f)
        return 1
    sys.stdout.write("PASS\n")
    sys.stdout.flush()
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="kvsvc.server", description="带过期时间的键值存储服务")
    ap.add_argument("--port", type=int, default=0, help="监听端口 (0 = 由系统分配)")
    ap.add_argument("--wal", type=str, default=None, help="WAL 文件路径")
    ap.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    ap.add_argument("--selftest", action="store_true", help="运行无头端到端自检")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    serve(args.host, args.port, args.wal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
