"""kvsvc.server —— HTTP 服务入口 (python3 -m kvsvc.server)。

路由契约:
  PUT    /kv/{key}       -> 200 {"key","value","expires_in"}
  GET    /kv/{key}       -> 200 {"key","value"} | 404 {"error":"not_found"}
  DELETE /kv/{key}       -> 200 {"deleted":true} | 404 {"error":"not_found"}
  POST   /kv/{key}/incr  -> 200 {"key","value"} | 409 {"error":"not_int"}
  GET    /stats          -> 200 {"count","expired","uptime_ms"}
  其它                    -> 404 {"error":"not_found"}

并发: ThreadingHTTPServer (每请求一线程, 支持 keep-alive HTTP/1.1)。
运行: python3 -m kvsvc.server --port 8000 --wal /tmp/kv.wal
自检: python3 -m kvsvc.server --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from .store import KVStore

JSON_CT = "application/json; charset=utf-8"
STORE: KVStore  # 由 main 注入


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ------------------------------------------------------------ helpers --

    def _send_json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _segments(path: str):
        parts = urlsplit(path).path.split("/")
        return [unquote(p) for p in parts if p != ""]

    # ------------------------------------------------------------- router --

    def _route(self, method: str) -> None:
        segs = self._segments(self.path)
        try:
            if method == "PUT" and len(segs) == 2 and segs[0] == "kv":
                body = self._read_json_body()
                if "value" not in body:
                    return self._send_json(400, {"error": "bad_request"})
                ttl = body.get("ttl")
                if ttl is not None:
                    if not isinstance(ttl, (int, float)) or isinstance(ttl, bool):
                        return self._send_json(400, {"error": "bad_request"})
                    ttl = float(ttl)
                res = STORE.put(segs[1], body.get("value"), ttl)
                return self._send_json(200, res)

            if method == "GET" and len(segs) == 2 and segs[0] == "kv":
                if not STORE.exists(segs[1]):
                    return self._send_json(404, {"error": "not_found"})
                return self._send_json(200, {"key": segs[1], "value": STORE.get(segs[1])})

            if method == "DELETE" and len(segs) == 2 and segs[0] == "kv":
                if STORE.delete(segs[1]):
                    return self._send_json(200, {"deleted": True})
                return self._send_json(404, {"error": "not_found"})

            if method == "POST" and len(segs) == 3 and segs[0] == "kv" and segs[2] == "incr":
                body = self._read_json_body()
                by = body.get("by", 1)
                if not isinstance(by, int) or isinstance(by, bool):
                    return self._send_json(400, {"error": "bad_request"})
                ok, value = STORE.incr(segs[1], by)
                if not ok:
                    return self._send_json(409, {"error": "not_int"})
                return self._send_json(200, {"key": segs[1], "value": value})

            if method == "GET" and len(segs) == 1 and segs[0] == "stats":
                return self._send_json(200, STORE.stats())

            return self._send_json(404, {"error": "not_found"})
        except Exception:  # noqa: BLE001 —— 内部异常转 500, 修正连接状态
            try:
                self._send_json(500, {"error": "internal"})
            except Exception:  # pragma: no cover
                pass

    # ------------------------------------------------------------ methods --

    def do_GET(self):     self._route("GET")
    def do_PUT(self):     self._route("PUT")
    def do_DELETE(self):  self._route("DELETE")
    def do_POST(self):    self._route("POST")

    def log_message(self, fmt, *args):  # 抑制访问日志噪声
        pass


# ====================================================================== #
# 无头自检: 启动真实服务 + 真实 HTTP 客户端, 覆盖契约各条
# ====================================================================== #

def _req(method: str, url: str, payload=None, timeout=10):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = JSON_CT
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type"), json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), json.loads(e.read().decode("utf-8"))


def _start_server(port: int, wal: str):
    global STORE
    store = KVStore(wal)
    store.replay()
    STORE = store
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, store


def _selftest() -> int:
    failures = []
    base = lambda p: f"http://127.0.0.1:{p}"  # noqa: E731

    with tempfile.TemporaryDirectory() as td:
        wal = os.path.join(td, "kv.wal")
        httpd, store = _start_server(0, wal)
        u = base(httpd.server_address[1])

        def check(name, cond, extra=""):
            if cond:
                print(f"PASS {name}")
            else:
                print(f"FAIL {name} {extra}")
                failures.append(name)

        # --- 1. PUT / GET / Content-Type ---
        st, ct, body = _req("PUT", f"{u}/kv/a", {"value": {"x": 1}, "ttl": 60})
        check("put_ct", ct == JSON_CT, ct)
        check("put_body", st == 200 and body["key"] == "a"
              and isinstance(body["expires_in"], (int, float)), body)
        st, ct, body = _req("GET", f"{u}/kv/a")
        check("get_ok", st == 200 and body["value"] == {"x": 1}, body)
        # 无 ttl -> expires_in 必须为 null
        st, _, body = _req("PUT", f"{u}/kv/nottl", {"value": 1})
        check("put_no_ttl_null", body["expires_in"] is None, body)

        # --- 2. 404 语义 (统一路由回落) ---
        st, ct, body = _req("GET", f"{u}/kv/missing")
        check("get_404", st == 404 and body == {"error": "not_found"} and ct == JSON_CT, (st, body))
        st, _, body = _req("DELETE", f"{u}/kv/missing")
        check("del_404", st == 404 and body == {"error": "not_found"}, (st, body))
        st, _, body = _req("GET", f"{u}/nope")
        check("path_404", st == 404 and body == {"error": "not_found"}, (st, body))
        st, _, body = _req("POST", f"{u}/kv/a")
        check("method_404", st == 404 and body == {"error": "not_found"}, (st, body))

        # --- 3. DELETE 成功 ---
        st, _, body = _req("DELETE", f"{u}/kv/a")
        check("del_ok", st == 200 and body == {"deleted": True}, (st, body))

        # --- 4. TTL 过期 + expired 计数 ---
        _req("PUT", f"{u}/kv/short", {"value": 1, "ttl": 0.3})
        st, _, _ = _req("GET", f"{u}/kv/short")
        check("ttl_alive", st == 200, st)
        time.sleep(0.6)
        st, _, body = _req("GET", f"{u}/kv/short")
        check("ttl_gone", st == 404, (st, body))
        st, _, body = _req("GET", f"{u}/stats")
        check("stats_expired", body["expired"] >= 1, body)
        check("stats_types", isinstance(body["count"], int) and isinstance(body["uptime_ms"], int)
              and body["uptime_ms"] >= 0, body)

        # --- 5. incr 语义 ---
        st, _, body = _req("POST", f"{u}/kv/cnt/incr", {})
        check("incr_default", st == 200 and body["value"] == 1, (st, body))
        st, _, body = _req("POST", f"{u}/kv/cnt/incr", {"by": 5})
        check("incr_by", st == 200 and body["value"] == 6, (st, body))
        _req("PUT", f"{u}/kv/str", {"value": "hello"})
        st, _, body = _req("POST", f"{u}/kv/str/incr", {})
        check("incr_not_int", st == 409 and body == {"error": "not_int"}, (st, body))

        # --- 6. 并发正确性: 8 客户端 x 20 incr = 160 (不得丢更新) ---
        _req("PUT", f"{u}/kv/conc", {"value": 0})
        errs = []

        def worker():
            try:
                for _ in range(20):
                    s, _, b = _req("POST", f"{u}/kv/conc/incr", {"by": 1})
                    if s != 200:
                        errs.append((s, b))
            except Exception as e:  # noqa: BLE001
                errs.append(repr(e))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        st, _, body = _req("GET", f"{u}/kv/conc")
        check("concurrent_incr", body["value"] == 160 and not errs, (body, errs[:3]))

        # --- 7. 持久化重启: incr 累计值保留; 过期键不复活 ---
        _req("PUT", f"{u}/kv/persist", {"value": {"n": 42}})
        _req("POST", f"{u}/kv/persist_incr/incr", {"by": 7})
        _req("PUT", f"{u}/kv/die", {"value": 9, "ttl": 0.3})
        time.sleep(0.6)

        httpd.shutdown()
        httpd.server_close()
        store.close()

        httpd2, store2 = _start_server(0, wal)  # 复用同一 WAL 重启
        u2 = base(httpd2.server_address[1])
        st, _, body = _req("GET", f"{u2}/kv/persist")
        check("replay_value", st == 200 and body["value"] == {"n": 42}, (st, body))
        st, _, body = _req("GET", f"{u2}/kv/persist_incr")
        check("replay_incr", st == 200 and body["value"] == 7, (st, body))
        st, _, body = _req("GET", f"{u2}/kv/die")
        check("replay_no_resurrect", st == 404, (st, body))

        # --- 8. WAL 行格式: 每行含 op + key, op 取值受限于三值 ---
        ops = set()
        bad_lines = 0
        with open(wal, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "op" not in rec or "key" not in rec or rec["op"] not in ("put", "delete", "incr"):
                    bad_lines += 1
                else:
                    ops.add(rec["op"])
        check("wal_ops", ops >= {"put", "delete", "incr"}, ops)
        check("wal_all_lines_valid", bad_lines == 0, bad_lines)

        httpd2.shutdown()
        httpd2.server_close()
        store2.close()

    print("SELFTEST", "PASS" if not failures else f"FAIL({len(failures)})")
    return 0 if not failures else 1


# ====================================================================== #
# 入口
# ====================================================================== #

def main(argv=None) -> int:
    global STORE
    ap = argparse.ArgumentParser(prog="kvsvc.server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--wal", type=str, default=None)
    ap.add_argument("--host", type=str, default="0.0.0.0")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    store = KVStore(args.wal)
    store.replay()
    STORE = store

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.daemon_threads = True

    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
