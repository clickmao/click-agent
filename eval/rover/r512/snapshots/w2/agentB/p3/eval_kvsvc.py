#!/usr/bin/env python3
"""kvsvc 端到端自检: 真启动子进程服务, 走 HTTP 契约校验。

运行: python3 eval_kvsvc.py   (退出码 0=PASS, 非 0=FAIL)
覆盖: READY 就绪 / Content-Type / 全部路由 / TTL 惰性过期 / 409 not_int /
      并发 8x20 incr 不丢更新 / WAL 重启重放 / 过期不复活 / WAL 行含 op,key。
"""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HOST = "127.0.0.1"
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def req(port, method, path, body=None):
    conn = http.client.HTTPConnection(HOST, port, timeout=5)
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    ct = resp.getheader("Content-Type")
    conn.close()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        parsed = None
    return resp.status, ct, parsed, raw


def start(port, wal):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.Popen(
        [sys.executable, "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    line = p.stdout.readline().strip()
    return p, line


def main():
    tmp = tempfile.mkdtemp(prefix="kvsvc_eval_")
    wal = os.path.join(tmp, "wal.log")
    port = 8791

    # 1) 启动 + READY
    p, ready = start(port, wal)
    check("ready_line", ready == "READY")
    try:
        # 2) PUT 无 ttl
        st, ct, body, _ = req(port, "PUT", "/kv/foo", {"value": {"a": 1}})
        check("put_status_200", st == 200)
        check("put_ct", ct == "application/json; charset=utf-8")
        check("put_body", body["key"] == "foo" and body["value"] == {"a": 1}
              and body["expires_in"] is None)

        # 3) GET
        st, ct, body, _ = req(port, "GET", "/kv/foo")
        check("get_200", st == 200 and body == {"key": "foo", "value": {"a": 1}})
        check("get_ct", ct == "application/json; charset=utf-8")

        # 4) 404 未命中 + 其它路径/方法
        st, _, body, _ = req(port, "GET", "/kv/missing")
        check("get_404", st == 404 and body == {"error": "not_found"})
        st, _, body, _ = req(port, "GET", "/nope")
        check("other_path_404", st == 404 and body == {"error": "not_found"})
        st, _, body, _ = req(port, "POST", "/stats")
        check("other_method_404", st == 404 and body == {"error": "not_found"})

        # 5) TTL 过期 + expired 计数
        st, _, body, _ = req(port, "PUT", "/kv/short", {"value": "x", "ttl": 0.2})
        check("put_ttl_expires_in", st == 200 and 0 < body["expires_in"] <= 0.2)
        time.sleep(0.35)
        st, _, body, _ = req(port, "GET", "/kv/short")
        check("ttl_invisible", st == 404 and body == {"error": "not_found"})
        st, _, body, _ = req(port, "GET", "/stats")
        check("stats_expired_counts", body["expired"] >= 1)
        check("stats_uptime_ms", isinstance(body["uptime_ms"], int)
              and body["uptime_ms"] >= 0)

        # 6) DELETE
        st, _, body, _ = req(port, "PUT", "/kv/del", {"value": 1})
        st, _, body, _ = req(port, "DELETE", "/kv/del")
        check("delete_200", st == 200 and body == {"deleted": True})
        st, _, body, _ = req(port, "DELETE", "/kv/del")
        check("delete_404", st == 404 and body == {"error": "not_found"})

        # 7) incr: 不存在按 0 / by 默认 1 / 非整数 409
        st, _, body, _ = req(port, "POST", "/kv/cnt/incr", {"by": 5})
        check("incr_new", st == 200 and body == {"key": "cnt", "value": 5})
        st, _, body, _ = req(port, "POST", "/kv/cnt/incr", {})
        check("incr_default_by", st == 200 and body["value"] == 6)
        req(port, "PUT", "/kv/strv", {"value": "hello"})
        st, _, body, _ = req(port, "POST", "/kv/strv/incr", {"by": 1})
        check("incr_not_int_409", st == 409 and body == {"error": "not_int"})

        # 8) 并发 8x20 incr 不丢更新
        errors = []

        def burst():
            try:
                for _ in range(20):
                    s, _, b, _ = req(port, "POST", "/kv/cc/incr", {"by": 1})
                    if s != 200:
                        errors.append((s, b))
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

        threads = [threading.Thread(target=burst) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        check("concurrent_no_error", not errors)
        st, _, body, _ = req(port, "GET", "/kv/cc")
        check("concurrent_exact_160", st == 200 and body["value"] == 160)

        # 记录重启前应保留的键
        req(port, "PUT", "/kv/persist", {"value": "P"})
        req(port, "PUT", "/kv/will_expire", {"value": "E", "ttl": 0.2})
        req(port, "PUT", "/kv/deleted", {"value": "D"})
        req(port, "DELETE", "/kv/deleted")
    finally:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()

    # 9) WAL 行格式
    ops = set()
    has_key = True
    with open(wal, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            ops.add(rec.get("op"))
            if "key" not in rec:
                has_key = False
    check("wal_has_key", has_key)
    check("wal_ops_subset", ops.issubset({"put", "delete", "incr"}))
    check("wal_ops_all_present", {"put", "delete", "incr"}.issubset(ops))

    # 10) 重启重放: 未过期键与 incr 累计值恢复; 过期键不复活; delete 不复活
    time.sleep(0.35)  # 让 will_expire 越过 TTL
    p2, ready2 = start(port, wal)
    check("ready_line_restart", ready2 == "READY")
    try:
        st, _, body, _ = req(port, "GET", "/kv/persist")
        check("replay_persist", st == 200 and body["value"] == "P")
        st, _, body, _ = req(port, "GET", "/kv/cnt")
        check("replay_incr_value", st == 200 and body["value"] == 6)
        st, _, body, _ = req(port, "GET", "/kv/cc")
        check("replay_cc_value", st == 200 and body["value"] == 160)
        st, _, body, _ = req(port, "GET", "/kv/will_expire")
        check("replay_expired_not_revived", st == 404)
        st, _, body, _ = req(port, "GET", "/kv/deleted")
        check("replay_deleted_absent", st == 404)
    finally:
        p2.terminate()
        try:
            p2.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p2.kill()

    if FAILS:
        print("FAIL: %d checks failed -> %s" % (len(FAILS), FAILS))
        return 1
    print("PASS: all contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
