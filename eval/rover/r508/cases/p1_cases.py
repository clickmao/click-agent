#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 P1 隐藏用例 (逐条机械判对) —— 在**产物目录**内以 `python3 -I -B` 运行。

判据 (只用标准库, 不读产物源码, 只驱动其真实行为):
  起服务 -> 打 HTTP -> 校验 状态码/Content-Type/JSON 体 -> 重启保活校验。
每条用例独立捕获异常; 输出 `CASE <name> PASS|FAIL <detail>`; 全 PASS 才 rc=0。
期望值来自**独立朴素路径** (本文件内 Counter/手写断言), 不是从被测产物里读出来的。
"""
from __future__ import annotations
import json, os, signal, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request

ENTRY = "app.py"
BASE = "http://127.0.0.1:%d"
TMP = tempfile.mkdtemp(prefix="p1case-")
DB = os.path.join(TMP, "todos.db")
PROC = {"p": None, "port": 0}
STOP = {"flag": False}


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start(port=None):
    port = port or free_port()
    p = subprocess.Popen([sys.executable, "-I", "-B", ENTRY, "--port", str(port), "--db", DB],
                         cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 25
    while time.time() < deadline:
        if p.poll() is not None:
            raise RuntimeError("server exited rc=%s out=%s" % (p.returncode, (p.stdout.read() or "")[-300:]))
        try:
            req = urllib.request.Request(BASE % port + "/todos")
            urllib.request.urlopen(req, timeout=1).read()
            PROC["p"], PROC["port"], STOP["flag"] = p, port, False
            return
        except urllib.error.HTTPError:
            PROC["p"], PROC["port"], STOP["flag"] = p, port, False
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("READY 超时 (25s)")


def stop(sig=signal.SIGTERM):
    p = PROC.get("p")
    if not p or p.poll() is not None:
        return
    try:
        p.send_signal(sig)
    except Exception:
        p.kill()
    try:
        p.wait(timeout=10)
    except Exception:
        p.kill()


def http(method, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    req = urllib.request.Request(BASE % PROC["port"] + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        r = urllib.request.urlopen(req, timeout=8)
        code, ctype = r.status, r.headers.get("Content-Type", "")
        blob = r.read()
    except urllib.error.HTTPError as e:
        code, ctype = e.code, e.headers.get("Content-Type", "")
        blob = e.read()
    try:
        obj = json.loads(blob.decode("utf-8"))
    except Exception:
        obj = None
    return code, ctype, obj


def cases():
    yield "create_first", c_create_first
    yield "create_second", c_create_second
    yield "list_order", c_list_order
    yield "get_one_and_404", c_get_one
    yield "mark_done_idempotent", c_mark_done
    yield "done_unknown_404", c_done_unknown
    yield "delete_and_404", c_delete
    yield "bad_request_400", c_bad_request
    yield "unknown_path_404", c_unknown_path
    yield "restart_persistence_no_id_reuse", c_restart


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _ctype_ok(ctype):
    return "application/json" in ctype.lower()


def c_create_first():
    code, ct, obj = http("POST", "/todos", {"text": "alpha"})
    need(code == 201, "code=%s" % code)
    need(_ctype_ok(ct), "content-type=%r" % ct)
    need(obj == {"id": 1, "text": "alpha", "done": False}, "body=%r" % (obj,))


def c_create_second():
    code, _, obj = http("POST", "/todos", {"text": "beta"})
    need(code == 201 and obj == {"id": 2, "text": "beta", "done": False}, "code=%s body=%r" % (code, obj))


def c_list_order():
    code, ct, obj = http("GET", "/todos")
    need(code == 200 and _ctype_ok(ct), "code=%s ct=%r" % (code, ct))
    want = [{"id": 1, "text": "alpha", "done": False}, {"id": 2, "text": "beta", "done": False}]
    need(obj == {"todos": want}, "body=%r" % (obj,))


def c_get_one():
    code, _, obj = http("GET", "/todos/1")
    need(code == 200 and obj == {"id": 1, "text": "alpha", "done": False}, "code=%s body=%r" % (code, obj))
    code, _, obj = http("GET", "/todos/999")
    need(code == 404 and obj == {"error": "not_found"}, "code=%s body=%r" % (code, obj))


def c_mark_done():
    code, _, obj = http("POST", "/todos/1/done")
    need(code == 200 and obj == {"id": 1, "text": "alpha", "done": True}, "code=%s body=%r" % (code, obj))
    code, _, obj = http("POST", "/todos/1/done")   # 幂等: 重复置 done 仍 200
    need(code == 200 and obj == {"id": 1, "text": "alpha", "done": True}, "2nd code=%s body=%r" % (code, obj))
    _, _, lst = http("GET", "/todos")
    need(lst["todos"][0]["done"] is True, "list=%r" % (lst,))


def c_done_unknown():
    code, _, obj = http("POST", "/todos/999/done")
    need(code == 404 and obj == {"error": "not_found"}, "code=%s body=%r" % (code, obj))


def c_delete():
    code, _, obj = http("DELETE", "/todos/2")
    need(code == 200 and obj == {"deleted": True}, "code=%s body=%r" % (code, obj))
    _, _, lst = http("GET", "/todos")
    need([t["id"] for t in lst["todos"]] == [1], "list=%r" % (lst,))
    code, _, obj = http("DELETE", "/todos/2")
    need(code == 404 and obj == {"error": "not_found"}, "2nd code=%s body=%r" % (code, obj))


def c_bad_request():
    code, _, obj = http("POST", "/todos", {})
    need(code == 400 and obj == {"error": "bad_request"}, "empty code=%s body=%r" % (code, obj))
    code, _, obj = http("POST", "/todos", {"text": "   "})
    need(code == 400 and obj == {"error": "bad_request"}, "blank code=%s body=%r" % (code, obj))
    code, _, obj = http("POST", "/todos", raw=b"{not json")
    need(code == 400 and obj == {"error": "bad_request"}, "malformed code=%s body=%r" % (code, obj))


def c_unknown_path():
    code, _, obj = http("GET", "/nope")
    need(code == 404 and obj == {"error": "not_found"}, "code=%s body=%r" % (code, obj))
    code, _, obj = http("POST", "/todos/1")
    need(code == 404 and obj == {"error": "not_found"}, "code=%s body=%r" % (code, obj))


def c_restart():
    stop()
    time.sleep(0.4)
    start()
    code, _, obj = http("POST", "/todos", {"text": "gamma"})
    need(code == 201 and obj["id"] == 3, "id 复用/未持久化: code=%s body=%r" % (code, obj))
    _, _, lst = http("GET", "/todos")
    got = [(t["id"], t["text"], t["done"]) for t in lst["todos"]]
    need(got == [(1, "alpha", True), (3, "gamma", False)], "重启后数据: %r" % (got,))


def main():
    if not os.path.exists(ENTRY):
        print("CASE entry_exists FAIL 缺 %s" % ENTRY)
        return 1
    code = 0
    try:
        start()
    except Exception as e:
        print("CASE server_start FAIL %s" % e)
        return 1
    try:
        for name, fn in cases():
            try:
                fn()
                print("CASE %s PASS" % name)
            except Exception as e:
                code = 1
                print("CASE %s FAIL %s: %s" % (name, type(e).__name__, str(e)[:300]))
    finally:
        stop(signal.SIGKILL)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
