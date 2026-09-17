#!/usr/bin/env python3
"""kvsvc 契约自检。运行: python3 kvsvc_selftest.py  (退出码 0=全绿)"""
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(ROOT, "data", "kvsvc_selftest")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
WAL = os.path.join(TMP, "wal.jsonl")

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(detail)) if detail else ""))
    return bool(cond)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Server:
    def __init__(self, port, wal):
        self.port = port
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline().strip()
        if line != "READY":
            raise RuntimeError("未收到 READY: %r" % line)
        self.ready_line = line

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()


def req(port, method, path, body=None, timeout=5):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    ct = resp.getheader("Content-Type")
    st = resp.status
    conn.close()
    return st, ct, raw


def j(raw):
    return json.loads(raw.decode("utf-8"))


def main():
    port = free_port()
    srv = Server(port, WAL)
    check("启动打印 READY", srv.ready_line == "READY")

    # 1) PUT / GET / 404
    st, ct, raw = req(port, "PUT", "/kv/a", {"value": {"x": 1}, "ttl": 10})
    body = j(raw)
    check("PUT 200 + 字段", st == 200 and body["key"] == "a" and body["value"] == {"x": 1}
          and isinstance(body["expires_in"], (int, float)) and 0 < body["expires_in"] <= 10, body)
    check("PUT Content-Type", ct == "application/json; charset=utf-8", ct)
    st, ct, raw = req(port, "GET", "/kv/a")
    check("GET 200 值一致", st == 200 and j(raw)["value"] == {"x": 1}, raw)
    st, ct, raw = req(port, "GET", "/kv/nope")
    check("GET 缺失 404 not_found + 头", st == 404 and j(raw) == {"error": "not_found"}
          and ct == "application/json; charset=utf-8", (st, ct, raw))
    st, _, raw = req(port, "DELETE", "/kv/nope")
    check("DELETE 缺失 404", st == 404 and j(raw) == {"error": "not_found"}, raw)
    st, _, raw = req(port, "PUT", "/kv/b", {"value": 5})
    check("无 ttl 键 expires_in 为 null", st == 200 and j(raw)["expires_in"] is None, raw)

    # 2) DELETE 命中
    req(port, "PUT", "/kv/del", {"value": 1})
    st, _, raw = req(port, "DELETE", "/kv/del")
    check("DELETE 200 deleted=true", st == 200 and j(raw) == {"deleted": True}, raw)
    check("删除后 GET 404", req(port, "GET", "/kv/del")[0] == 404)

    # 3) TTL 过期 + expired 计数
    req(port, "PUT", "/kv/t", {"value": "v", "ttl": 0.3})
    check("TTL 内可见", req(port, "GET", "/kv/t")[0] == 200)
    time.sleep(0.7)
    check("TTL 后不可见", req(port, "GET", "/kv/t")[0] == 404)
    st, _, raw = req(port, "GET", "/stats")
    stats = j(raw)
    check("stats 结构", st == 200 and set(stats) == {"count", "expired", "uptime_ms"}
          and all(isinstance(stats[k], int) for k in stats), stats)
    check("expired 累计 >=1", stats["expired"] >= 1, stats)

    # 4) incr
    st, _, raw = req(port, "POST", "/kv/c/incr", {})
    check("incr 默认 by=1 从 0 起算", st == 200 and j(raw) == {"key": "c", "value": 1}, raw)
    st, _, raw = req(port, "POST", "/kv/c/incr", {"by": 5})
    check("incr 累加", st == 200 and j(raw)["value"] == 6, raw)
    req(port, "PUT", "/kv/s", {"value": "str"})
    st, _, raw = req(port, "POST", "/kv/s/incr", {"by": 1})
    check("incr 非整数 409 not_int", st == 409 and j(raw) == {"error": "not_int"}, (st, raw))

    # 5) 未知路径/方法
    for m, p in [("GET", "/nope"), ("POST", "/kv/a"), ("PUT", "/stats"),
                 ("PATCH", "/kv/a"), ("OPTIONS", "/whatever")]:
        st, ct, raw = req(port, m, p)
        check("未知路由 %s %s -> 404 JSON" % (m, p),
              st == 404 and j(raw) == {"error": "not_found"}
              and ct == "application/json; charset=utf-8", (st, ct, raw))

    # 6) 并发正确性: 8 客户端 × 20 次 incr
    req(port, "DELETE", "/kv/cc")
    errors = []

    def worker():
        try:
            for _ in range(20):
                st, _, raw = req(port, "POST", "/kv/cc/incr", {"by": 1})
                if st != 200:
                    errors.append((st, raw))
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    _, _, raw = req(port, "GET", "/kv/cc")
    got = j(raw)["value"]
    check("并发 8x20 incr = 160", got == 160 and not errors,
          {"value": got, "errors": errors[:3], "sec": round(time.time() - t0, 3)})

    # 7) WAL 格式
    with open(WAL, "r", encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    ops_ok = True
    bad = []
    for ln in lines:
        rec = json.loads(ln)
        if rec.get("op") not in ("put", "delete", "incr") or not isinstance(rec.get("key"), str):
            ops_ok = False
            bad.append(ln)
    check("WAL 每行含合法 op/key (%d 行)" % len(lines), ops_ok and len(lines) > 0, bad[:2])

    # 8) 重启重放
    req(port, "PUT", "/kv/p1", {"value": 7, "ttl": 100})
    req(port, "POST", "/kv/p1/incr", {"by": 3})          # -> 10
    req(port, "PUT", "/kv/pexp", {"value": "gone", "ttl": 0.3})
    req(port, "PUT", "/kv/pdel", {"value": 1})
    req(port, "DELETE", "/kv/pdel")
    time.sleep(0.7)
    srv.stop()
    srv2 = Server(port, WAL)
    check("重启后 READY", srv2.ready_line == "READY")
    st, _, raw = req(port, "GET", "/kv/p1")
    check("重启重放 put+incr 累计值=10", st == 200 and j(raw)["value"] == 10, (st, raw))
    check("重启后过期键不复活", req(port, "GET", "/kv/pexp")[0] == 404)
    check("重启后已删除键仍不在", req(port, "GET", "/kv/pdel")[0] == 404)
    stats2 = j(req(port, "GET", "/stats")[2])
    check("重启后 stats 合法", set(stats2) == {"count", "expired", "uptime_ms"}
          and stats2["count"] >= 2, stats2)
    srv2.stop()

    failed = [n for n, ok in RESULTS if not ok]
    print("----")
    print("TOTAL %d, PASS %d, FAIL %d" % (len(RESULTS), len(RESULTS) - len(failed), len(failed)))
    if failed:
        print("FAILED: " + "; ".join(failed))
    print("WAL = " + WAL)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
