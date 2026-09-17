"""kvsvc 无头自检：python3 -m kvsvc.selftest

覆盖:
  1. READY 就绪行
  2. PUT/GET/DELETE 基本语义 + 404
  3. TTL 过期（惰性 + expired 计数）
  4. incr 语义（不存在起算、非整数 409、累计）
  5. 并发正确性：8 客户端 x 20 incr == 160（不丢更新）
  6. WAL 重放：重启后未过期键（含 incr 累计值）恢复；已过期键不复活
  7. Content-Type 契约
退出码 0=PASS, 1=FAIL。
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error

HOST = "127.0.0.1"
CT_EXPECT = "application/json; charset=utf-8"

_fail = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print("[%s] %s %s" % (status, name, detail))
    if not cond:
        _fail.append(name)


def _req(method, url, body=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers.get("Content-Type"), json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {}
        return e.code, e.headers.get("Content-Type"), parsed


def start_server(port, wal):
    proc = subprocess.Popen(
        [sys.executable, "-m", "kvsvc.server", "--port", str(port), "--wal", wal],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    )
    line = proc.stdout.readline()
    if line.strip() != "READY":
        raise RuntimeError("no READY, got %r" % line)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def main():
    port = 18080 + (os.getpid() % 500)
    tmpdir = tempfile.mkdtemp(prefix="kvsvc_st_")
    wal = os.path.join(tmpdir, "test.wal")
    base = "http://%s:%d" % (HOST, port)

    proc = start_server(port, wal)
    try:
        # 2. 基本语义
        st, ct, body = _req("PUT", base + "/kv/a", {"value": {"x": 1}})
        check("put.ct", ct == CT_EXPECT, ct)
        check("put.200", st == 200 and body["key"] == "a" and body["value"] == {"x": 1}
              and body["expires_in"] is None, str(body))
        st, ct, body = _req("GET", base + "/kv/a")
        check("get.ok", st == 200 and body == {"key": "a", "value": {"x": 1}}, str(body))
        st, _, body = _req("GET", base + "/kv/missing")
        check("get.404", st == 404 and body == {"error": "not_found"}, str(body))
        st, _, body = _req("DELETE", base + "/kv/none")
        check("del.404", st == 404 and body == {"error": "not_found"}, str(body))
        st, _, body = _req("DELETE", base + "/kv/a")
        check("del.200", st == 200 and body == {"deleted": True}, str(body))
        st, _, body = _req("GET", base + "/kv/a")
        check("del.gone", st == 404, str(body))

        # 3. TTL
        st, _, body = _req("PUT", base + "/kv/ttl1", {"value": 1, "ttl": 1.0})
        check("ttl.set", st == 200 and 0 < body["expires_in"] <= 1.0, str(body))
        time.sleep(1.2)
        st, _, body = _req("GET", base + "/kv/ttl1")
        check("ttl.expired", st == 404, str(body))
        st, _, body = _req("GET", base + "/stats")
        check("ttl.counted", body["expired"] >= 1 and body["count"] == 0, str(body))

        # 4. incr
        st, _, body = _req("POST", base + "/kv/n", {"by": 5})
        check("incr.new", st == 200 and body["value"] == 5, str(body))
        st, _, body = _req("POST", base + "/kv/n", {"by": 2})
        check("incr.acc", st == 200 and body["value"] == 7, str(body))
        st, _, body = _req("PUT", base + "/kv/s", {"value": "str"})
        st, _, body = _req("POST", base + "/kv/s", {"by": 1})
        check("incr.notint", st == 409 and body == {"error": "not_int"}, str(body))
        st, _, body = _req("POST", base + "/kv/d", {})
        check("incr.defby", st == 200 and body["value"] == 1, str(body))

        # 5. 并发正确性
        _req("PUT", base + "/kv/cnt", {"value": 0})
        errors = []

        def worker():
            try:
                for _ in range(20):
                    st, _, b = _req("POST", base + "/kv/cnt", {"by": 1})
                    if st != 200:
                        errors.append((st, b))
            except Exception as e:  # noqa
                errors.append(repr(e))

        ts = [threading.Thread(target=worker) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        st, _, body = _req("GET", base + "/kv/cnt")
        check("concurrent.160", (not errors) and body["value"] == 160,
              "value=%s errors=%s" % (body.get("value"), errors[:3]))

        # 7. Content-Type on 404
        st, ct, body = _req("GET", base + "/nope")
        check("404.ct", ct == CT_EXPECT and body == {"error": "not_found"}, ct)

        # stats uptime
        st, _, body = _req("GET", base + "/stats")
        check("stats.uptime", isinstance(body["uptime_ms"], int) and body["uptime_ms"] >= 0,
              str(body))
    finally:
        stop_server(proc)

    # 6. WAL 重放
    #   此时 WAL 内应有 n=7 -> +5 +2, cnt=160, d=1；s 被 put 为字符串；a 被删。
    proc2 = start_server(port, wal)
    try:
        st, _, body = _req("GET", base + "/kv/n")
        check("replay.incr", st == 200 and body["value"] == 7, str(body))
        st, _, body = _req("GET", base + "/kv/cnt")
        check("replay.cnt", st == 200 and body["value"] == 160, str(body))
        st, _, body = _req("GET", base + "/kv/a")
        check("replay.del", st == 404, str(body))
        st, _, body = _req("GET", base + "/kv/d")
        check("replay.d", st == 200 and body["value"] == 1, str(body))
    finally:
        stop_server(proc2)

    # 已过期键不复活：写一个 ttl=1 键，关闭，等过期，重启
    proc3 = start_server(port, wal)
    _req("PUT", base + "/kv/dead", {"value": 9, "ttl": 0.5})
    stop_server(proc3)
    time.sleep(0.8)
    proc4 = start_server(port, wal)
    try:
        st, _, body = _req("GET", base + "/kv/dead")
        check("replay.no_revive", st == 404, str(body))
        # WAL 行格式核查
        with open(wal, "r", encoding="utf-8") as f:
            lines = [json.loads(x) for x in f if x.strip()]
        ops = set(r.get("op") for r in lines)
        check("wal.ops", ops <= {"put", "delete", "incr"} and {"put", "delete", "incr"} <= ops,
              str(ops))
        check("wal.key", all("key" in r for r in lines))
    finally:
        stop_server(proc4)

    if _fail:
        print("\nSELFTEST FAIL: %d 项: %s" % (len(_fail), ", ".join(_fail)))
        return 1
    print("\nSELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
