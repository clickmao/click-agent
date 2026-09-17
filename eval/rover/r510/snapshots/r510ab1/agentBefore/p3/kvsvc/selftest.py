"""kvsvc 契约自检：python3 -m kvsvc.selftest

无头、可重复。退出码 0=全部 PASS，非 0=有 FAIL。
覆盖：启动 READY、JSON Content-Type、PUT/GET/DELETE/incr/stats、
      TTL 过期、404/409、并发 incr 不丢更新、WAL 重放（过期不复活）。
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def req(method, url, body=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, resp.headers.get("Content-Type"), raw
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def start_server(port, wal):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    p = subprocess.Popen(
        [sys.executable, "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    line = p.stdout.readline().strip()
    return p, line


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_ready(port, timeout=5.0):
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req("GET", base + "/stats")
            return True
        except Exception:
            time.sleep(0.05)
    return False


def main():
    tmp = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmp, "wal.jsonl")
    port = free_port()
    proc, ready_line = start_server(port, wal)
    base = f"http://127.0.0.1:{port}"

    try:
        # 1) READY
        check("startup prints READY", ready_line == "READY", repr(ready_line))

        # 2) PUT/GET + Content-Type
        code, ctype, raw = req("PUT", base + "/kv/a", {"value": {"x": 1}})
        body = json.loads(raw.decode("utf-8"))
        check("PUT 200 + json ctype",
              code == 200 and ctype == "application/json; charset=utf-8"
              and body["key"] == "a" and body["value"] == {"x": 1}
              and body["expires_in"] is None, f"{code} {ctype} {body}")

        code, _, raw = req("GET", base + "/kv/a")
        check("GET returns value", code == 200 and json.loads(raw)["value"] == {"x": 1})

        # 3) 404 不存在
        code, _, raw = req("GET", base + "/kv/nope")
        check("GET missing 404", code == 404 and json.loads(raw) == {"error": "not_found"})

        # 4) DELETE
        code, _, raw = req("DELETE", base + "/kv/a")
        check("DELETE 200", code == 200 and json.loads(raw) == {"deleted": True})
        code, _, raw = req("DELETE", base + "/kv/a")
        check("DELETE again 404", code == 404)

        # 5) TTL 过期
        code, _, raw = req("PUT", base + "/kv/t", {"value": 1, "ttl": 0.4})
        body = json.loads(raw)
        check("PUT ttl expires_in numeric", 0 < body["expires_in"] <= 0.4, str(body))
        time.sleep(0.6)
        code, _, raw = req("GET", base + "/kv/t")
        check("GET expired 404", code == 404)
        code, _, raw = req("GET", base + "/stats")
        st = json.loads(raw)
        check("stats expired>=1", st["expired"] >= 1, str(st))
        check("stats fields", set(st) == {"count", "expired", "uptime_ms"}, str(st))

        # 6) incr：不存在按 0，非整数 409
        code, _, raw = req("POST", base + "/kv/c/incr", {})
        check("incr from 0 default by=1", code == 200 and json.loads(raw)["value"] == 1)
        code, _, raw = req("POST", base + "/kv/c/incr", {"by": 4})
        check("incr by 4", json.loads(raw)["value"] == 5)
        req("PUT", base + "/kv/s", {"value": "str"})
        code, _, raw = req("POST", base + "/kv/s/incr", {"by": 1})
        check("incr non-int 409", code == 409 and json.loads(raw) == {"error": "not_int"})

        # 7) 并发 incr 不丢更新：8 线程 x 20 次 +1
        errors = []

        def worker():
            try:
                for _ in range(20):
                    c, _, _ = req("POST", base + "/kv/conc/incr", {"by": 1})
                    if c != 200:
                        errors.append(c)
            except Exception as e:  # noqa
                errors.append(repr(e))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        code, _, raw = req("GET", base + "/kv/conc")
        val = json.loads(raw)["value"]
        check("concurrent incr exact 160", val == 160 and not errors,
              f"value={val} errors={errors}")

        # 8) 未知路径/方法 404
        code, _, raw = req("GET", base + "/unknown")
        check("unknown path 404", code == 404)
        code, _, raw = req("PATCH", base + "/kv/a")
        check("unknown method 404", code == 404)

        # 9) WAL 行格式：op in {put,delete,incr} 且含 key
        with open(wal, "r", encoding="utf-8") as fp:
            lines = [json.loads(l) for l in fp if l.strip()]
        check("WAL lines have op+key",
              len(lines) > 0 and all(
                  l.get("op") in ("put", "delete", "incr") and "key" in l for l in lines))

        # 10) 重启重放：持久键恢复、incr 累计恢复、过期键不复活
        req("PUT", base + "/kv/persist", {"value": "keep"})
        req("PUT", base + "/kv/short", {"value": "gone", "ttl": 0.3})
        req("POST", base + "/kv/counter/incr", {"by": 7})
        time.sleep(0.5)
        proc.terminate()
        proc.wait(timeout=5)

        proc2, line2 = start_server(free_port(), wal)
        # 注意：重启后端口变了，重建 base 需重新取端口；这里直接用同一读法
        # 为简单起见，重启用同一端口（旧进程已退出）
        proc2.terminate()
        proc2.wait(timeout=5)
        port2 = free_port()
        proc2, line2 = start_server(port2, wal)
        base2 = f"http://127.0.0.1:{port2}"
        check("restart READY", line2 == "READY", repr(line2))

        code, _, raw = req("GET", base2 + "/kv/persist")
        check("replay keeps persistent", code == 200 and json.loads(raw)["value"] == "keep",
              f"{code} {raw}")
        code, _, raw = req("GET", base2 + "/kv/counter")
        check("replay restores incr total 7",
              code == 200 and json.loads(raw)["value"] == 7, f"{code} {raw}")
        code, _, raw = req("GET", base2 + "/kv/short")
        check("replay expired not revived", code == 404, f"{code} {raw}")

        proc2.terminate()
        proc2.wait(timeout=5)

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass

    print()
    if FAILS:
        print(f"RESULT: FAIL ({len(FAILS)}): {FAILS}")
        return 1
    print("RESULT: PASS  (all checks green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
