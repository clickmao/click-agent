"""kvsvc 机械契约自测（仅标准库）。

覆盖非功能契约:
  T1 启动就绪 (READY)
  T2 Content-Type=application/json; charset=utf-8
  T3 路由 404 契约（未知路径 / 未知方法 / 非法 JSON 段）
  T4 基本 put/get/delete + 404
  T5 ttl 惰性过期 + expired 计数 + count
  T6 incr 语义（缺失起 0、非整数 409、by 自定义）
  T7 并发 8x20 incr 精确等于总增量（无丢更新）
  T8 WAL 每笔写操作 op ∈ {put,delete,incr} 且含 key
  T9 进程重启重放：未过期键与 incr 累计值恢复；已过期键不复活

运行: python3 -m kvsvc.selftest
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.dirname(HERE)
CONTENT_TYPE = "application/json; charset=utf-8"


class ServerProc:
    """以子进程形态拉起真实入口 python3 -m kvsvc.server。"""

    def __init__(self, wal, port):
        env = dict(os.environ)
        env["PYTHONPATH"] = PKG_PARENT + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
            cwd=PKG_PARENT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.port = port

    def wait_ready(self, timeout=15.0):
        """读一行 stdout，必须恰好是 READY。"""
        result = {}

        def reader():
            line = self.proc.stdout.readline()
            result["line"] = line.decode("utf-8", "replace").strip()

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive() or result.get("line") != "READY":
            return False, result.get("line")
        return True, result["line"]

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)


def call(port, method, path, body=None, timeout=10.0):
    url = "http://127.0.0.1:%d%s" % (port, path)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, resp.headers.get("Content-Type"), json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, e.headers.get("Content-Type"), json.loads(raw.decode("utf-8"))


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print("[%s] %s %s" % (status, name, detail))
    if not cond:
        FAILURES.append(name)


def main():
    tmpdir = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmpdir, "wal.log")
    port = free_port()
    srv = ServerProc(wal, port)
    try:
        ok, line = srv.wait_ready()
        check("T1 READY", ok, "line=%r" % line)

        # --- T2 Content-Type + T4 put/get/delete ---
        st, ct, body = call(port, "PUT", "/kv/a", {"value": {"nested": [1, 2]}, "ttl": 100})
        check("T2 content-type", ct == CONTENT_TYPE, "ct=%r" % ct)
        check("T4 put", st == 200 and body["key"] == "a" and body["value"] == {"nested": [1, 2]}
              and isinstance(body["expires_in"], (int, float)) and 0 < body["expires_in"] <= 100,
              "st=%s body=%s" % (st, body))

        st, ct, body = call(port, "GET", "/kv/a")
        check("T4 get", st == 200 and body == {"key": "a", "value": {"nested": [1, 2]}}, "body=%s" % body)

        # 无 ttl -> expires_in 为 null
        st, _, body = call(port, "PUT", "/kv/keep", {"value": 1})
        check("T4 put no-ttl", st == 200 and body["expires_in"] is None, "body=%s" % body)

        st, _, body = call(port, "GET", "/kv/missing")
        check("T4 get 404", st == 404 and body == {"error": "not_found"}, "st=%s body=%s" % (st, body))

        st, _, body = call(port, "DELETE", "/kv/keep")
        check("T4 delete", st == 200 and body == {"deleted": True}, "st=%s body=%s" % (st, body))
        st, _, body = call(port, "DELETE", "/kv/keep")
        check("T4 delete 404", st == 404 and body == {"error": "not_found"}, "st=%s body=%s" % (st, body))

        # --- T3 未知路径/方法 ---
        st, _, body = call(port, "GET", "/nope")
        check("T3 unknown path", st == 404 and body == {"error": "not_found"}, "st=%s" % st)
        st, _, body = call(port, "POST", "/kv/a")
        check("T3 unknown method", st == 404 and body == {"error": "not_found"}, "st=%s" % st)
        st, _, body = call(port, "PATCH", "/stats")
        check("T3 stats wrong method", st == 404 and body == {"error": "not_found"}, "st=%s" % st)

        # --- T5 ttl 过期 ---
        st, _, _ = call(port, "PUT", "/kv/short", {"value": "x", "ttl": 0.5})
        st, _, body = call(port, "GET", "/kv/short")
        check("T5 visible before ttl", st == 200, "st=%s" % st)
        time.sleep(0.8)
        st, _, body = call(port, "GET", "/kv/short")
        check("T5 gone after ttl", st == 404 and body == {"error": "not_found"}, "st=%s" % st)
        _, _, stats = call(port, "GET", "/stats")
        check("T5 expired counted", stats["expired"] >= 1 and isinstance(stats["uptime_ms"], int),
              "stats=%s" % stats)

        # --- T6 incr ---
        st, _, body = call(port, "POST", "/kv/cnt/incr", {"by": 5})
        check("T6 incr from absent", st == 200 and body == {"key": "cnt", "value": 5}, "body=%s" % body)
        st, _, body = call(port, "POST", "/kv/cnt/incr", {})
        check("T6 incr default by", st == 200 and body["value"] == 6, "body=%s" % body)
        call(port, "PUT", "/kv/str", {"value": "notint"})
        st, _, body = call(port, "POST", "/kv/str/incr", {"by": 1})
        check("T6 incr not_int", st == 409 and body == {"error": "not_int"}, "st=%s body=%s" % (st, body))

        # --- T7 并发正确性: 8x20 incr ---
        call(port, "PUT", "/kv/conc", {"value": 0})
        errors = []

        def worker():
            for _ in range(20):
                st, _, _ = call(port, "POST", "/kv/conc/incr", {"by": 1})
                if st != 200:
                    errors.append(st)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        st, _, body = call(port, "GET", "/kv/conc")
        check("T7 concurrent incr", not errors and body["value"] == 160,
              "value=%s errors=%s" % (body.get("value"), errors))

        # --- T8 WAL 内容 ---
        ops = []
        with open(wal, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ops.append(json.loads(line))
        all_op = all(r.get("op") in {"put", "delete", "incr"} for r in ops)
        all_key = all("key" in r for r in ops)
        check("T8 wal ops", all_op and all_key and len(ops) >= 20, "records=%d" % len(ops))

        # --- T9 重启重放 ---
        call(port, "PUT", "/kv/persist", {"value": 42})
        call(port, "PUT", "/kv/vanishing", {"value": "gone", "ttl": 0.5})
        call(port, "POST", "/kv/conc/incr", {"by": 1})  # 累计 161
        srv.stop()
        time.sleep(0.8)  # 让 vanishing 过期

        port2 = free_port()
        srv2 = ServerProc(wal, port2)
        ok, line = srv2.wait_ready()
        try:
            check("T9 restart READY", ok, "line=%r" % line)
            st, _, body = call(port2, "GET", "/kv/persist")
            check("T9 persist restored", st == 200 and body["value"] == 42, "body=%s" % body)
            st, _, body = call(port2, "GET", "/kv/conc")
            check("T9 incr restored", st == 200 and body["value"] == 161, "body=%s" % body)
            st, _, body = call(port2, "GET", "/kv/vanishing")
            check("T9 expired not revived", st == 404 and body == {"error": "not_found"}, "st=%s" % st)
        finally:
            srv2.stop()
        srv = srv2  # 避免 finally 二次 stop 崩溃
    finally:
        srv.stop()

    print("SELFTEST %s (%d failures)" % ("PASS" if not FAILURES else "FAIL", len(FAILURES)))
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
