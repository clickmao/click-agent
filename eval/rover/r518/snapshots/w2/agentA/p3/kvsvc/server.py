"""kvsvc.server —— 基于 http.server.ThreadingHTTPServer 的 HTTP 入口。

启动: python3 -m kvsvc.server --port {int} --wal {path}
就绪后 stdout 打印一行 READY 并 flush。

自检: python3 -m kvsvc.server --selftest
  (无头, 覆盖 TTL/并发 incr/WAL 重放/路由与状态码, 打印 PASS/FAIL, 退出码 0/非0)
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .store import KVStore

_CT = "application/json; charset=utf-8"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"
    # 由 run() 注入
    store = None
    started_at = 0.0

    # ---------- 工具 ----------
    def log_message(self, fmt, *args):  # 静默: 不打印多余文字
        pass

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", _CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self):
        self._send(404, {"error": "not_found"})

    def _read_json_body(self):
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            raw = self.rfile.read(int(length))
        except (ValueError, OSError):
            return {}
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    # ---------- 路由解析 ----------
    def _route(self):
        """解析 path -> (kind, key)。返回 None 表示未知路径。"""
        path = self.path.split("?", 1)[0]
        if not path.startswith("/"):
            path = "/" + path
        if path == "/stats":
            return ("stats", None)
        if path.startswith("/kv/"):
            key = path[len("/kv/"):]
            if key.endswith("/incr"):
                return ("incr", key[:-len("/incr")])
            return ("kv", key)
        return None

    # ---------- 方法 ----------
    def do_GET(self):
        r = self._route()
        if r is None:
            return self._not_found()
        kind, key = r
        if kind == "stats":
            s = self.store.stats()
            uptime = int((time.time() - self.started_at) * 1000)
            return self._send(200, {
                "count": s["count"], "expired": s["expired"],
                "uptime_ms": uptime,
            })
        if kind == "kv":
            res = self.store.get(key)
            if res is None:
                return self._not_found()
            return self._send(200, res)
        return self._not_found()

    def do_PUT(self):
        r = self._route()
        if r is None:
            return self._not_found()
        kind, key = r
        if kind != "kv":
            return self._not_found()
        body = self._read_json_body()
        ttl = body.get("ttl")
        if ttl is not None:
            if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                return self._send(400, {"error": "bad_request"})
        res = self.store.put(key, body.get("value"), ttl)
        return self._send(200, res)

    def do_DELETE(self):
        r = self._route()
        if r is None:
            return self._not_found()
        kind, key = r
        if kind != "kv":
            return self._not_found()
        if self.store.delete(key):
            return self._send(200, {"deleted": True})
        return self._not_found()

    def do_POST(self):
        r = self._route()
        if r is None:
            return self._not_found()
        kind, key = r
        if kind != "incr":
            return self._not_found()
        body = self._read_json_body()
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            return self._send(400, {"error": "bad_request"})
        try:
            res = self.store.incr(key, by)
        except ValueError:
            return self._send(409, {"error": "not_int"})
        return self._send(200, res)


def make_server(port, wal_path, host="127.0.0.1"):
    store = KVStore(wal_path)
    _Handler.store = store
    _Handler.started_at = time.time()
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.daemon_threads = True
    return httpd, store


def run(port, wal_path, host="127.0.0.1"):
    httpd, store = make_server(port, wal_path, host)
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        store.close()


# ==================== 自检 ====================
def _http(method, url, obj=None):
    data = None
    headers = {}
    if obj is not None:
        data = json.dumps(obj).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            return resp.status, resp.headers.get("Content-Type"), json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw)
        except ValueError:
            body = None
        return e.code, e.headers.get("Content-Type"), body


def _selftest():
    import tempfile

    failures = []

    def check(name, cond, extra=""):
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {name}{(' :: ' + extra) if extra else ''}")
        if not cond:
            failures.append(name)

    tmpdir = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmpdir, "wal.jsonl")
    base = "http://127.0.0.1:18931"

    httpd, store = make_server(18931, wal)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        # 1. PUT / GET 基本 + Content-Type
        code, ct, body = _http("PUT", base + "/kv/a", {"value": {"x": 1}, "ttl": 5})
        check("put returns 200 + ctype", code == 200 and ct == _CT, f"{code} {ct}")
        check("put body expires_in", isinstance(body.get("expires_in"), (int, float))
              and 0 < body["expires_in"] <= 5, str(body))
        code, ct, body = _http("GET", base + "/kv/a")
        check("get returns value", code == 200 and body["value"] == {"x": 1}, str(body))

        # 2. 无 ttl -> expires_in null
        code, ct, body = _http("PUT", base + "/kv/nt", {"value": 7})
        check("no-ttl -> expires_in null", body.get("expires_in") is None, str(body))

        # 3. GET 不存在 -> 404 not_found
        code, ct, body = _http("GET", base + "/kv/missing")
        check("get missing -> 404", code == 404 and body == {"error": "not_found"}
              and ct == _CT, f"{code} {body}")

        # 4. DELETE 存在/不存在
        code, ct, body = _http("DELETE", base + "/kv/nt")
        check("delete ok", code == 200 and body == {"deleted": True}, str(body))
        code, ct, body = _http("DELETE", base + "/kv/nt")
        check("delete missing -> 404", code == 404 and body == {"error": "not_found"},
              str(body))

        # 5. incr: 不存在按 0 起算; 非整数 -> 409
        code, ct, body = _http("POST", base + "/kv/cnt/incr", {"by": 5})
        check("incr from zero", code == 200 and body["value"] == 5, str(body))
        _http("PUT", base + "/kv/str", {"value": "hello"})
        code, ct, body = _http("POST", base + "/kv/str/incr", {"by": 1})
        check("incr non-int -> 409 not_int",
              code == 409 and body == {"error": "not_int"}, f"{code} {body}")

        # 6. TTL 到期不可见并入 expired
        _http("PUT", base + "/kv/ttl", {"value": 1, "ttl": 0.3})
        time.sleep(0.45)
        code, ct, body = _http("GET", base + "/kv/ttl")
        check("ttl expired -> 404", code == 404, f"{code} {body}")
        _, _, st = _http("GET", base + "/stats")
        check("expired counted >=1", st["expired"] >= 1, str(st))
        check("stats has uptime_ms int", isinstance(st["uptime_ms"], int), str(st))

        # 7. 未知路径/方法 -> 404
        code, ct, body = _http("GET", base + "/nope")
        check("unknown path -> 404", code == 404 and body == {"error": "not_found"},
              str(body))
        code, ct, body = _http("POST", base + "/kv/a", {"value": 1})
        check("wrong method -> 404", code == 404, f"{code} {body}")

        # 8. 并发 incr 不丢更新: 8 客户端 x 20 次
        _http("PUT", base + "/kv/conc", {"value": 0})
        errs = []

        def worker():
            try:
                for _ in range(20):
                    c, _, _b = _http("POST", base + "/kv/conc/incr", {"by": 1})
                    if c != 200:
                        errs.append(c)
            except Exception as e:  # noqa: BLE001
                errs.append(repr(e))

        ths = [threading.Thread(target=worker) for _ in range(8)]
        for th in ths:
            th.start()
        for th in ths:
            th.join()
        _, _, body = _http("GET", base + "/kv/conc")
        check("concurrent incr == 160",
              body["value"] == 160 and not errs, f"{body} errs={errs}")

        # 9. WAL 行含 op/key
        with open(wal, "r", encoding="utf-8") as fh:
            lines = [json.loads(x) for x in fh if x.strip()]
        ok_wal = all(isinstance(r.get("op"), str) and r["op"] in ("put", "delete", "incr")
                     and isinstance(r.get("key"), str) for r in lines)
        check("wal lines have op/key", ok_wal and len(lines) > 0, f"n={len(lines)}")
    finally:
        httpd.shutdown()
        httpd.server_close()
        store.close()

    # 10. 重放: 重启后恢复未过期键 (含 incr 累计), 过期键不复活
    _put_before = None
    store2 = KVStore(wal)
    got = store2.get("conc")
    check("replay restores incr total", got is not None and got["value"] == 160,
          str(got))
    check("replay drops expired key", store2.get("ttl") is None, "ttl")
    check("replay keeps live key", store2.get("a") is not None, "a")
    store2.close()

    # 11. 重启后 TTL 键不复活 (过期时刻已过)
    wal2 = os.path.join(tmpdir, "wal2.jsonl")
    s = KVStore(wal2)
    s.put("k", "v", 0.2)
    s.close()
    time.sleep(0.35)
    s2 = KVStore(wal2)
    check("replay drops expired ttl key", s2.get("k") is None, "k")
    s2.close()

    print("SELFTEST " + ("PASS" if not failures else "FAIL")
          + ("" if not failures else " :: " + ",".join(failures)))
    return 0 if not failures else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kvsvc.server")
    ap.add_argument("--port", type=int)
    ap.add_argument("--wal")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.port is None or args.wal is None:
        ap.error("--port 与 --wal 为必填")
    run(args.port, args.wal, args.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
