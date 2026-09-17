"""HTTP 服务入口: python3 -m kvsvc.server --port {int} --wal {path}

契约要点:
  * 就绪后 stdout 打印一行 READY 并 flush。
  * 所有响应 Content-Type: application/json; charset=utf-8, body UTF-8。
  * ThreadingHTTPServer 处理并发 (契约 2/5)。
  * 路由见 handle_*。其它路径/方法 -> 404 {"error":"not_found"}。
  * 无多余 stdout 输出 (日志走 stderr)。

自检: python3 -m kvsvc.server --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional, Tuple

from .store import KVStore

_JSON_CT = "application/json; charset=utf-8"
# /kv/{key} 或 /kv/{key}/incr
_KV_RE = re.compile(r"^/kv/([^/]+)(?:/(incr))?$")
_START_TS = time.monotonic()


class KVHandler(BaseHTTPRequestHandler):
    """单请求处理器。服务端状态通过 server.store 访问 (共享, 由 store 自己加锁)。"""

    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ------------------------------------------------------------ 响应工具

    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", _JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Optional[dict]:
        """读取并解析请求体; 非法时返回 None (调用方回 400)。"""
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            n = int(length)
        except ValueError:
            return None
        raw = self.rfile.read(n) if n > 0 else b""
        if not raw.strip():
            return {}
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return obj if isinstance(obj, dict) else None

    # ------------------------------------------------------------- 日志抑制

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        # 默认实现会写 stderr; 保留便于排障, 但绝不写 stdout
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(),
                                                self.log_date_time_string(),
                                                fmt % args))

    # ----------------------------------------------------------- 路由分派

    def _route(self, method: str) -> None:
        path = self.path.split("?", 1)[0]
        m = _KV_RE.match(path)

        if path == "/stats" and method == "GET":
            st = self.server.store.stats()
            self._send_json(200, {
                "count": st["count"],
                "expired": st["expired"],
                "uptime_ms": int((time.monotonic() - _START_TS) * 1000),
            })
            return

        if m is not None:
            key, sub = m.group(1), m.group(2)
            if sub is None:
                if method == "PUT":
                    self._do_put(key)
                    return
                if method == "GET":
                    self._do_get(key)
                    return
                if method == "DELETE":
                    self._do_delete(key)
                    return
            elif sub == "incr" and method == "POST":
                self._do_incr(key)
                return

        self._send_json(404, {"error": "not_found"})

    # ------------------------------------------------------------- 各路由实现

    def _do_put(self, key: str) -> None:
        body = self._read_json_body()
        if body is None or "value" not in body:
            self._send_json(400, {"error": "bad_request"})
            return
        ttl = body.get("ttl")
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, (int, float))):
            self._send_json(400, {"error": "bad_request"})
            return
        resp = self.server.store.put(key, body["value"], ttl)
        self._send_json(200, resp)

    def _do_get(self, key: str) -> None:
        resp = self.server.store.get(key)
        if resp is None:
            self._send_json(404, {"error": "not_found"})
            return
        self._send_json(200, resp)

    def _do_delete(self, key: str) -> None:
        if self.server.store.delete(key):
            self._send_json(200, {"deleted": True})
        else:
            self._send_json(404, {"error": "not_found"})

    def _do_incr(self, key: str) -> None:
        body = self._read_json_body()
        if body is None:
            self._send_json(400, {"error": "bad_request"})
            return
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            self._send_json(400, {"error": "bad_request"})
            return
        status, resp = self.server.store.incr(key, by)
        if status == "not_int":
            self._send_json(409, {"error": "not_int"})
            return
        self._send_json(200, resp)

    # HTTP 动词入口

    def do_GET(self) -> None:  # noqa: N802
        self._route("GET")

    def do_PUT(self) -> None:  # noqa: N802
        self._route("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._route("DELETE")

    def do_POST(self) -> None:  # noqa: N802
        self._route("POST")


class KVServer(ThreadingHTTPServer):
    """ThreadingHTTPServer + 共享 store。daemon_threads 保证退出不挂住。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: Tuple[str, int], store: KVStore) -> None:
        super().__init__(addr, KVHandler)
        self.store = store


# ------------------------------------------------------------------ 自检


def _req(base: str, method: str, path: str, body: Optional[dict] = None):
    """返回 (status, json_obj, content_type)。"""
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, json.loads(raw.decode("utf-8")), r.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            obj = json.loads(raw.decode("utf-8"))
        except ValueError:
            obj = None
        return e.code, obj, e.headers.get("Content-Type")


def _selftest() -> int:
    """无头自检: 退出码 0=全过。覆盖契约 1-6。"""
    import os
    import shutil
    import tempfile

    failures: list = []

    def check(name: str, cond: bool, extra: str = "") -> None:
        if cond:
            print("PASS - %s" % name)
        else:
            print("FAIL - %s %s" % (name, extra))
            failures.append(name)

    tmp = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmp, "wal.jsonl")
    store = KVStore(wal)
    srv = KVServer(("127.0.0.1", 0), store)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = "http://127.0.0.1:%d" % port

    try:
        # --- 契约 2/3: PUT / GET / 头部
        st, obj, ct = _req(base, "PUT", "/kv/a", {"value": {"x": 1}, "ttl": 100})
        check("put_basic_200", st == 200 and obj["key"] == "a" and obj["value"] == {"x": 1},
              repr((st, obj)))
        check("content_type_json", ct == _JSON_CT, repr(ct))
        check("put_expires_in_num",
              isinstance(obj["expires_in"], (int, float)) and obj["expires_in"] <= 100,
              repr(obj["expires_in"]))

        st, obj, _ = _req(base, "PUT", "/kv/nottl", {"value": 5})
        check("put_no_ttl_null", st == 200 and obj["expires_in"] is None, repr(obj))

        st, obj, _ = _req(base, "GET", "/kv/a")
        check("get_basic", st == 200 and obj == {"key": "a", "value": {"x": 1}}, repr(obj))

        st, obj, _ = _req(base, "GET", "/kv/missing")
        check("get_404", st == 404 and obj == {"error": "not_found"}, repr((st, obj)))

        # --- 契约 3: DELETE
        st, obj, _ = _req(base, "DELETE", "/kv/a")
        check("delete_200", st == 200 and obj == {"deleted": True}, repr((st, obj)))
        st, obj, _ = _req(base, "DELETE", "/kv/a")
        check("delete_again_404", st == 404 and obj == {"error": "not_found"}, repr((st, obj)))

        # --- 契约 3: INCR
        st, obj, _ = _req(base, "POST", "/kv/c/incr", {})
        check("incr_from_zero", st == 200 and obj == {"key": "c", "value": 1}, repr((st, obj)))
        st, obj, _ = _req(base, "POST", "/kv/c/incr", {"by": 4})
        check("incr_by_4", st == 200 and obj["value"] == 5, repr((st, obj)))
        _req(base, "PUT", "/kv/s", {"value": "str"})
        st, obj, _ = _req(base, "POST", "/kv/s/incr", {"by": 1})
        check("incr_not_int_409", st == 409 and obj == {"error": "not_int"}, repr((st, obj)))
        _req(base, "PUT", "/kv/f", {"value": 1.5})
        st, obj, _ = _req(base, "POST", "/kv/f/incr", {"by": 1})
        check("incr_float_409", st == 409, repr((st, obj)))

        # --- 契约 3: 未知路径/方法
        st, obj, _ = _req(base, "GET", "/nope")
        check("unknown_path_404", st == 404 and obj == {"error": "not_found"}, repr((st, obj)))
        st, obj, _ = _req(base, "POST", "/kv/a")
        check("unknown_method_404", st == 404 and obj == {"error": "not_found"},
              repr((st, obj)))

        # --- 契约 4: TTL 过期不可见 + 计入 expired
        _req(base, "PUT", "/kv/t", {"value": 9, "ttl": 0.3})
        st_before, _, _ = _req(base, "GET", "/kv/t")
        time.sleep(0.6)
        st_after, obj_after, _ = _req(base, "GET", "/kv/t")
        st_stats, obj_stats, _ = _req(base, "GET", "/stats")
        check("ttl_visible_before_expiry", st_before == 200, repr(st_before))
        check("ttl_hidden_after_expiry",
              st_after == 404 and obj_after == {"error": "not_found"}, repr((st_after, obj_after)))
        check("expired_counted", obj_stats["expired"] >= 1, repr(obj_stats))

        # --- 契约 3: /stats 字段
        check("stats_shape",
              isinstance(obj_stats["count"], int) and isinstance(obj_stats["uptime_ms"], int)
              and obj_stats["uptime_ms"] >= 0, repr(obj_stats))

        # --- 契约 5: 并发正确性 (8 客户端 x 20 incr)
        _req(base, "PUT", "/kv/conc", {"value": 0})
        errors: list = []

        def worker() -> None:
            for _ in range(20):
                try:
                    s, o, _ = _req(base, "POST", "/kv/conc/incr", {"by": 1})
                    if s != 200:
                        errors.append((s, o))
                except Exception as e:  # noqa: BLE001
                    errors.append(repr(e))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        st, obj, _ = _req(base, "GET", "/kv/conc")
        check("concurrent_incr_exact",
              not errors and st == 200 and obj["value"] == 160,
              repr((errors[:3], st, obj)))

        # --- 契约 6: WAL 行格式
        with open(wal, "r", encoding="utf-8") as fp:
            lines = [json.loads(x) for x in fp if x.strip()]
        ops_ok = all(isinstance(r, dict) and r.get("op") in {"put", "delete", "incr"}
                     and isinstance(r.get("key"), str) for r in lines)
        seen_ops = {r.get("op") for r in lines}
        check("wal_lines_valid", bool(lines) and ops_ok, repr(lines[:2]))
        check("wal_all_ops_seen", seen_ops == {"put", "delete", "incr"}, repr(seen_ops))

    finally:
        srv.shutdown()
        srv.server_close()
        store.close()

    # --- 契约 6: 重启重放 (未过期恢复 + incr 累计; 已过期不复活)
    try:
        _req(base, "PUT", "/kv/keep", {"value": "v", "ttl": 60})  # noqa: F821
    except Exception:
        pass
    srv2 = None
    try:
        # 用同一个 WAL 新建 store (模拟重启)
        store2 = KVStore(wal)
        srv2 = KVServer(("127.0.0.1", 0), store2)
        port2 = srv2.server_address[1]
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        base2 = "http://127.0.0.1:%d" % port2

        st, obj, _ = _req(base2, "GET", "/kv/conc")
        check("replay_incr_value", st == 200 and obj.get("value") == 160, repr((st, obj)))
        st, obj, _ = _req(base2, "GET", "/kv/t")
        check("replay_expired_not_revived", st == 404, repr((st, obj)))
        st_del, obj_del, _ = _req(base2, "GET", "/kv/a")
        check("replay_deleted_stays_deleted", st_del == 404, repr((st_del, obj_del)))
        st_stats2, obj_stats2, _ = _req(base2, "GET", "/stats")
        check("replay_expired_counted", obj_stats2["expired"] >= 1, repr(obj_stats2))
    finally:
        if srv2 is not None:
            srv2.shutdown()
            srv2.server_close()
        store2.close()

    shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("FAIL: %d check(s) failed: %s" % (len(failures), ", ".join(failures)))
        return 1
    print("PASS: all checks passed")
    return 0


# ------------------------------------------------------------------ main


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m kvsvc.server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--wal", type=str, default="kvsvc.wal")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    store = KVStore(args.wal)
    srv = KVServer(("0.0.0.0", args.port), store)
    # 就绪信号: 必须先于 serve_forever 打印, 且 flush (契约 1)
    print("READY", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
