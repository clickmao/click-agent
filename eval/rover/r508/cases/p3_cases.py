#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 P3 隐藏用例 (逐条机械判对) —— 在**产物目录**内以 `python3 -I -B` 运行。

判据: 起 kvsvc 服务 (python3 -B -m kvsvc.server --port --wal) -> 打 HTTP -> 校验行为;
      含 TTL 过期 / 并发原子 incr / WAL 落盘 / 重启重放 四类硬用例。
用例脚本不读产物源码, 只驱动真实行为; 期望值在本文件内独立算出。
输出: 每行 `CASE <name> PASS` 或 `CASE <name> FAIL <reason>`; 全部 PASS 才 rc=0。
"""
from __future__ import annotations
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

ENTRY = os.path.join("kvsvc", "server.py")
FAILS = []


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Srv:
    def __init__(self, port, wal):
        self.port = port
        self.wal = wal
        self.p = subprocess.Popen(
            [sys.executable, "-B", "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
            cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": os.getcwd(), "LANG": "C.UTF-8"})
        t0 = time.time()
        while time.time() - t0 < 25:
            if self.p.poll() is not None:
                raise AssertionError("server exited rc=%s stderr=%s" % (self.p.returncode, (self.p.stderr.read() or "")[-300:]))
            try:
                with urllib.request.urlopen(self.url("/stats"), timeout=1) as r:
                    r.read()
                return
            except Exception:
                time.sleep(0.15)
        raise AssertionError("server not ready in 25s")

    def url(self, path):
        return "http://127.0.0.1:%d%s" % (self.port, path)

    def err_tail(self):
        try:
            if self.p.poll() is not None:
                return (self.p.stderr.read() or "")[-300:]
        except Exception:
            pass
        return ""

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.url(path), data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Connection", "close")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode("utf-8")
                ct = r.headers.get("Content-Type") or ""
                return r.status, ct, (json.loads(raw) if raw.strip() else None)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            return e.code, (e.headers.get("Content-Type") or ""), (json.loads(raw) if raw.strip() else None)
        except Exception as e:
            raise AssertionError("请求失败(%s: %s); server_stderr=%s" % (type(e).__name__, e, self.err_tail()))

    def stop(self):
        try:
            self.p.send_signal(signal.SIGTERM)
            self.p.wait(timeout=8)
        except Exception:
            try:
                self.p.kill()
            except Exception:
                pass


def _ctx():
    port = free_port()
    d = tempfile.mkdtemp(prefix="p3_")
    wal = os.path.join(d, "kv.wal")
    return Srv(port, wal), wal


def c_entry_present():
    need(os.path.isfile(ENTRY), "缺少入口 %s (契约要求 python3 -m kvsvc.server)" % ENTRY)


def c_put_get():
    s, _ = _ctx()
    try:
        st, ct, b = s.call("PUT", "/kv/a", {"value": 1})
        need(st == 200, "PUT st=%s" % st)
        need("application/json" in ct, "ct=%s" % ct)
        need(b.get("value") == 1 and b.get("key") == "a", "put body=%s" % b)
        need(b.get("expires_in") is None, "无 ttl 时 expires_in 应为 null, got=%s" % b.get("expires_in"))
        st, _, b = s.call("GET", "/kv/a")
        need(st == 200 and b.get("value") == 1, "GET st=%s body=%s" % (st, b))
    finally:
        s.stop()


def c_missing_404():
    s, _ = _ctx()
    try:
        st, _, b = s.call("GET", "/kv/nope")
        need(st == 404 and b.get("error") == "not_found", "GET missing st=%s body=%s" % (st, b))
        st, _, b = s.call("DELETE", "/kv/nope")
        need(st == 404 and b.get("error") == "not_found", "DELETE missing st=%s body=%s" % (st, b))
    finally:
        s.stop()


def c_unknown_path_404():
    s, _ = _ctx()
    try:
        st, _, b = s.call("GET", "/nope")
        need(st == 404 and b.get("error") == "not_found", "st=%s body=%s" % (st, b))
        st, _, b = s.call("POST", "/kv/a", {"x": 1})
        need(st == 404, "POST /kv/a st=%s" % st)
    finally:
        s.stop()


def c_ttl_expire():
    s, _ = _ctx()
    try:
        st, _, b = s.call("PUT", "/kv/t", {"value": "x", "ttl": 0.4})
        need(st == 200, "PUT st=%s" % st)
        need(b.get("expires_in") is not None and 0 < float(b["expires_in"]) <= 0.4 * 1.5,
             "expires_in 应为剩余秒数(>0 且不超 ttl 的 1.5 倍), got=%s" % b.get("expires_in"))
        st, _, b = s.call("GET", "/kv/t")
        need(st == 200 and b.get("value") == "x", "TTL 未到期却不可见 st=%s body=%s" % (st, b))
        time.sleep(0.8)
        st, _, b = s.call("GET", "/kv/t")
        need(st == 404, "TTL 到期后应 404, got st=%s body=%s" % (st, b))
        st, _, b = s.call("GET", "/stats")
        need(st == 200 and int(b.get("expired", 0)) >= 1, "expired 计数未增: %s" % b)
    finally:
        s.stop()


def c_incr_semantics():
    s, _ = _ctx()
    try:
        st, _, b = s.call("POST", "/kv/cnt/incr", {})
        need(st == 200 and b.get("value") == 1, "首次 incr st=%s body=%s" % (st, b))
        st, _, b = s.call("POST", "/kv/cnt/incr", {"by": 5})
        need(st == 200 and b.get("value") == 6, "按 5 incr st=%s body=%s" % (st, b))
        st, _, b = s.call("PUT", "/kv/s", {"value": "abc"})
        need(st == 200, "PUT s st=%s" % st)
        st, _, b = s.call("POST", "/kv/s/incr", {})
        need(st == 409 and b.get("error") == "not_int", "非整数 incr st=%s body=%s" % (st, b))
    finally:
        s.stop()


def c_incr_concurrent_atomic():
    s, _ = _ctx()
    try:
        errs = []

        def w():
            for _ in range(20):
                try:
                    st, _, _b = s.call("POST", "/kv/cc/incr", {"by": 1})
                    if st != 200:
                        errs.append(st)
                except Exception as e:
                    errs.append(str(e))

        ts = [threading.Thread(target=w) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        need(not errs, "并发请求出错: %s" % errs[:3])
        st, _, b = s.call("GET", "/kv/cc")
        need(st == 200 and b.get("value") == 160, "并发 incr 丢更新: value=%s (期望 160)" % (b.get("value"),))
    finally:
        s.stop()


def c_delete_flow():
    s, _ = _ctx()
    try:
        s.call("PUT", "/kv/d", {"value": [1, 2]})
        st, _, b = s.call("DELETE", "/kv/d")
        need(st == 200 and b.get("deleted") is True, "DELETE st=%s body=%s" % (st, b))
        st, _, b = s.call("GET", "/kv/d")
        need(st == 404, "删除后 GET st=%s" % st)
    finally:
        s.stop()


def c_stats_count():
    s, _ = _ctx()
    try:
        for k in ("k1", "k2", "k3"):
            s.call("PUT", "/kv/" + k, {"value": 1})
        s.call("PUT", "/kv/tmp", {"value": 1, "ttl": 0.3})
        time.sleep(0.7)
        st, _, b = s.call("GET", "/stats")
        need(st == 200, "stats st=%s" % st)
        need(b.get("count") == 3, "count 应为 3 (过期的不计), got=%s" % b.get("count"))
        need(int(b.get("expired", 0)) >= 1, "expired=%s" % b.get("expired"))
        need(isinstance(b.get("uptime_ms"), int) and b["uptime_ms"] >= 0, "uptime_ms=%s" % b.get("uptime_ms"))
    finally:
        s.stop()


def c_wal_lines():
    s, wal = _ctx()
    try:
        s.call("PUT", "/kv/w", {"value": 1})
        s.call("POST", "/kv/w/incr", {"by": 2})
        s.call("DELETE", "/kv/w")
        time.sleep(0.4)
        need(os.path.isfile(wal), "WAL 文件不存在: %s" % wal)
        with open(wal, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
        need(len(lines) >= 3, "WAL 行数不足: %d" % len(lines))
        ops = []
        for l in lines:
            rec = json.loads(l)
            need(isinstance(rec, dict), "WAL 行不是 JSON 对象: %r" % l[:80])
            ops.append(rec.get("op"))
        need("put" in ops and "incr" in ops, "WAL 缺 put/incr 记录: %s" % ops)
    finally:
        s.stop()


def c_restart_recovery():
    s, wal = _ctx()
    port = s.port
    try:
        s.call("PUT", "/kv/r1", {"value": "v1"})
        s.call("PUT", "/kv/r2", {"value": {"x": 2}})
        s.call("POST", "/kv/rc/incr", {"by": 3})
        s.stop()
        s2 = Srv(port, wal)
        try:
            st, _, b = s2.call("GET", "/kv/r1")
            need(st == 200 and b.get("value") == "v1", "重启后丢失 r1: st=%s body=%s" % (st, b))
            st, _, b = s2.call("GET", "/kv/r2")
            need(st == 200 and b.get("value") == {"x": 2}, "重启后 r2 值错: %s" % b)
            st, _, b = s2.call("POST", "/kv/rc/incr", {"by": 1})
            need(st == 200 and b.get("value") == 4, "重启后 incr 未接续: st=%s body=%s" % (st, b))
        finally:
            s2.stop()
    finally:
        s.stop()


def c_restart_drops_expired():
    s, wal = _ctx()
    port = s.port
    try:
        s.call("PUT", "/kv/live", {"value": 1})
        s.call("PUT", "/kv/gone", {"value": 1, "ttl": 0.3})
        time.sleep(0.8)
        s.stop()
        s2 = Srv(port, wal)
        try:
            st, _, _ = s2.call("GET", "/kv/live")
            need(st == 200, "重启后 live 应还在, st=%s" % st)
            st, _, _ = s2.call("GET", "/kv/gone")
            need(st == 404, "重启后已过期键不应复活, st=%s" % st)
        finally:
            s2.stop()
    finally:
        s.stop()


CASES = [
    ("entry_present", c_entry_present),
    ("put_get_json_api", c_put_get),
    ("missing_404", c_missing_404),
    ("unknown_path_404", c_unknown_path_404),
    ("ttl_expire_and_count", c_ttl_expire),
    ("incr_semantics_and_409", c_incr_semantics),
    ("incr_concurrent_atomic", c_incr_concurrent_atomic),
    ("delete_flow", c_delete_flow),
    ("stats_live_count", c_stats_count),
    ("wal_lines_jsonl", c_wal_lines),
    ("restart_recovery", c_restart_recovery),
    ("restart_drops_expired", c_restart_drops_expired),
]


def main():
    for name, fn in CASES:
        try:
            fn()
            print("CASE %s PASS" % name, flush=True)
        except Exception as e:
            print("CASE %s FAIL %s" % (name, str(e).replace("\n", " ")[:300]), flush=True)
            FAILS.append(name)
    print("SUMMARY %d/%d" % (len(CASES) - len(FAILS), len(CASES)), flush=True)
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
