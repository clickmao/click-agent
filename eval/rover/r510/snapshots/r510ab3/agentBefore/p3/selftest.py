"""无头自检: 启动 kvsvc.server 子进程, 按契约逐项校验。退出码 0=PASS。

运行: python3 selftest.py  (工作目录 = 仓库根)
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

WS = os.path.dirname(os.path.abspath(__file__))
PORT = 18731
WAL = os.path.join(tempfile.gettempdir(), "kvsvc_selftest.wal")
if os.path.exists(WAL):
    os.remove(WAL)

fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else " :: " + str(detail)))
    if not cond:
        fails.append(name)


def req(method, path, body=None, port=PORT):
    url = f"http://127.0.0.1:{port}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, dict(e.headers), json.loads(raw.decode("utf-8"))


def start():
    p = subprocess.Popen(
        [sys.executable, "-m", "kvsvc.server", "--port", str(PORT), "--wal", WAL],
        cwd=WS, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    line = p.stdout.readline().strip()
    if line != "READY":
        raise RuntimeError("no READY: " + repr(line) + " stderr=" + p.stderr.read())
    return p


def stop(p):
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()


p = start()

st, h, b = req("PUT", "/kv/a", {"value": {"x": 1}})
check("put_basic", st == 200 and b["key"] == "a" and b["value"] == {"x": 1} and b["expires_in"] is None, (st, b))
check("ct_json", h.get("Content-Type") == "application/json; charset=utf-8", h.get("Content-Type"))
st, h, b = req("GET", "/kv/a")
check("get_basic", st == 200 and b == {"key": "a", "value": {"x": 1}}, (st, b))

st, h, b = req("GET", "/kv/missing")
check("get_404", st == 404 and b == {"error": "not_found"}, (st, b))
st, h, b = req("DELETE", "/kv/missing")
check("del_404", st == 404 and b == {"error": "not_found"}, (st, b))
st, h, b = req("GET", "/nope")
check("route_404", st == 404 and b == {"error": "not_found"}, (st, b))

st, h, b = req("DELETE", "/kv/a")
check("del_ok", st == 200 and b == {"deleted": True}, (st, b))

st, h, b = req("POST", "/kv/cnt/incr", {"by": 5})
check("incr_new", st == 200 and b["value"] == 5, (st, b))
st, h, b = req("POST", "/kv/cnt/incr", {})
check("incr_default_by", st == 200 and b["value"] == 6, (st, b))
req("PUT", "/kv/str", {"value": "hello"})
st, h, b = req("POST", "/kv/str/incr", {"by": 1})
check("incr_not_int", st == 409 and b == {"error": "not_int"}, (st, b))

req("PUT", "/kv/t1", {"value": 7, "ttl": 0.4})
st, h, b = req("GET", "/kv/t1")
check("ttl_alive", st == 200 and b["value"] == 7, (st, b))
st, h, b = req("PUT", "/kv/t2", {"value": 8, "ttl": 0.4})
check("ttl_expires_in_num", isinstance(b["expires_in"], (int, float)) and 0 < b["expires_in"] <= 0.4, b)
time.sleep(0.7)
st, h, b = req("GET", "/kv/t1")
check("ttl_gone", st == 404 and b == {"error": "not_found"}, (st, b))
st, h, b = req("GET", "/stats")
check("stats_expired_count", b["count"] == 1 and b["expired"] >= 2, b)

errors = []


def worker():
    try:
        for _ in range(20):
            req("POST", "/kv/conc/incr", {})
    except Exception as e:  # pragma: no cover
        errors.append(e)


req("PUT", "/kv/conc", {"value": 0})
ts = [threading.Thread(target=worker) for _ in range(8)]
for t in ts:
    t.start()
for t in ts:
    t.join()
st, h, b = req("GET", "/kv/conc")
check("concurrent_incr", not errors and b.get("value") == 160, (b, errors))

req("PUT", "/kv/persist", {"value": "keep"})
req("PUT", "/kv/expired_rt", {"value": "x", "ttl": 0.3})
time.sleep(0.6)
stop(p)
p = start()

st, h, b = req("GET", "/kv/persist")
check("wal_restore_put", st == 200 and b["value"] == "keep", (st, b))
st, h, b = req("GET", "/kv/conc")
check("wal_restore_incr", st == 200 and b["value"] == 160, (st, b))
st, h, b = req("GET", "/kv/expired_rt")
check("wal_no_revive", st == 404, (st, b))

ops = set()
ok_lines = True
with open(WAL, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if "op" not in d or "key" not in d or d["op"] not in ("put", "delete", "incr"):
            ok_lines = False
        ops.add(d["op"])
check("wal_format", ok_lines, "bad line")
check("wal_all_ops", ops == {"put", "delete", "incr"}, ops)

stop(p)
print("RESULT:", "PASS" if not fails else "FAIL " + ",".join(fails))
sys.exit(0 if not fails else 1)
