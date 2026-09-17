"""kvsvc 无头自检: 覆盖契约各条(含并发与持久化重放)。

运行:  python3 -m kvsvc.selftest
输出末行 PASS/FAIL; 退出码 0=通过, 非 0=失败。

使用标准库 http.client + ThreadingHTTPServer(同进程), 不联网外部主机。
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from http.client import HTTPConnection

from . import server as server_mod

FAILURES = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print("  ok   - %s" % name)
    else:
        print("  FAIL - %s %s" % (name, detail))
        FAILURES.append(name)


def _request(port: int, method: str, path: str, body=None, ct_header=True):
    """返回 (status, headers, parsed_body_text)。"""
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        headers = {}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(payload))
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        return resp.status, dict(resp.getheaders()), raw
    finally:
        conn.close()


def _start(server):
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t


def test_http_contract(tmp_wal):
    server = server_mod.build_server(0, tmp_wal)
    port = server.server_address[1]
    _start(server)
    try:
        # 1) PUT 无 ttl
        st, hd, raw = _request(port, "PUT", "/kv/a", {"value": {"x": 1}})
        check("PUT 200", st == 200, "got %s" % st)
        check(
            "Content-Type 契约",
            hd.get("Content-Type") == "application/json; charset=utf-8",
            "got %r" % hd.get("Content-Type"),
        )
        body = json.loads(raw)
        check("PUT key", body.get("key") == "a", repr(body))
        check("PUT value 原样", body.get("value") == {"x": 1}, repr(body))
        check("PUT 无 ttl expires_in=None", body.get("expires_in") is None, repr(body))

        # 2) GET 命中
        st, _, raw = _request(port, "GET", "/kv/a")
        check("GET 200", st == 200 and json.loads(raw)["value"] == {"x": 1}, raw)

        # 3) GET 未命中
        st, _, raw = _request(port, "GET", "/kv/missing")
        check("GET 404", st == 404 and json.loads(raw) == {"error": "not_found"}, raw)

        # 4) DELETE
        st, _, raw = _request(port, "DELETE", "/kv/a")
        check("DELETE 200", st == 200 and json.loads(raw) == {"deleted": True}, raw)
        st, _, raw = _request(port, "DELETE", "/kv/a")
        check("DELETE 二次 404", st == 404, raw)

        # 5) incr 从 0 起算 + by
        st, _, raw = _request(port, "POST", "/kv/n/incr", {"by": 5})
        check("incr 默认路径", st == 200 and json.loads(raw)["value"] == 5, raw)
        st, _, raw = _request(port, "POST", "/kv/n/incr", {})
        check("incr 默认 by=1", st == 200 and json.loads(raw)["value"] == 6, raw)

        # 6) incr 非整数 -> 409
        _request(port, "PUT", "/kv/s", {"value": "str"})
        st, _, raw = _request(port, "POST", "/kv/s/incr", {"by": 1})
        check("incr 非整数 409", st == 409 and json.loads(raw) == {"error": "not_int"}, raw)

        # 7) stats
        st, _, raw = _request(port, "GET", "/stats")
        body = json.loads(raw)
        check(
            "stats 形状",
            st == 200 and set(body) == {"count", "expired", "uptime_ms"}
            and isinstance(body["count"], int) and isinstance(body["expired"], int)
            and isinstance(body["uptime_ms"], int),
            raw,
        )

        # 8) 未知路径 / 方法
        st, _, raw = _request(port, "GET", "/nope")
        check("未知路径 404", st == 404 and json.loads(raw) == {"error": "not_found"}, raw)
        st, _, raw = _request(port, "POST", "/kv/a")
        check("未知方法 404", st == 404, raw)

        # 9) TTL 过期 + expired 计数
        _request(port, "PUT", "/kv/t", {"value": 1, "ttl": 0.3})
        st, _, raw = _request(port, "GET", "/kv/t")
        check("TTL 未过期可见", st == 200, raw)
        before = json.loads(_request(port, "GET", "/stats")[2])["expired"]
        time.sleep(0.45)
        st, _, raw = _request(port, "GET", "/kv/t")
        check("TTL 过期不可见", st == 404, raw)
        after = json.loads(_request(port, "GET", "/stats")[2])["expired"]
        check("expired 计数递增", after == before + 1, "%s -> %s" % (before, after))

        # 10) PUT 带 ttl 的 expires_in 为数字
        _request(port, "PUT", "/kv/e", {"value": 2, "ttl": 10})
        st, _, raw = _request(port, "PUT", "/kv/e", {"value": 2, "ttl": 10})
        body = json.loads(raw)
        check(
            "expires_in 数字",
            isinstance(body.get("expires_in"), (int, float)) and body["expires_in"] <= 10,
            raw,
        )
    finally:
        server.shutdown()
        server.server_close()


def test_concurrency(tmp_wal):
    server = server_mod.build_server(0, tmp_wal)
    port = server.server_address[1]
    _start(server)
    clients, per = 8, 20
    errors = []

    def worker():
        try:
            for _ in range(per):
                st, _, raw = _request(port, "POST", "/kv/c/incr", {"by": 1})
                if st != 200:
                    errors.append((st, raw))
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    try:
        threads = [threading.Thread(target=worker) for _ in range(clients)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        st, _, raw = _request(port, "GET", "/kv/c")
        value = json.loads(raw)["value"] if st == 200 else None
        check(
            "并发 8x20 无丢更新",
            not errors and value == clients * per,
            "errors=%r value=%r" % (errors[:3], value),
        )
    finally:
        server.shutdown()
        server.server_close()


def test_wal_and_replay(tmp_wal):
    server = server_mod.build_server(0, tmp_wal)
    port = server.server_address[1]
    _start(server)
    try:
        _request(port, "PUT", "/kv/p", {"value": {"deep": [1, 2]}})
        _request(port, "POST", "/kv/i/incr", {"by": 7})
        _request(port, "POST", "/kv/i/incr", {"by": 3})
        _request(port, "PUT", "/kv/dead", {"value": 1, "ttl": 0.3})
        _request(port, "DELETE", "/kv/p")
        _request(port, "PUT", "/kv/live", {"value": "keep"})
    finally:
        server.shutdown()
        server.server_close()

    # WAL 内容校验
    ops, keys, bad = set(), set(), 0
    with open(tmp_wal, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            line = line.lstrip("\ufeff")
            rec = json.loads(line)
            ops.add(rec.get("op"))
            keys.add(rec.get("key"))
            if "op" not in rec or "key" not in rec:
                bad += 1
    check("WAL op 取值合法", ops <= {"put", "delete", "incr"} and ops, repr(ops))
    check("WAL 每行含 op/key", bad == 0, "bad=%d" % bad)

    time.sleep(0.45)  # 让 ttl=0.3 的键过期

    # 重启(新 store 从同一 WAL 重放)
    server2 = server_mod.build_server(0, tmp_wal)
    port2 = server2.server_address[1]
    _start(server2)
    try:
        st, _, raw = _request(port2, "GET", "/kv/i")
        check("重放 incr 累计值=10", st == 200 and json.loads(raw)["value"] == 10, raw)
        st, _, raw = _request(port2, "GET", "/kv/p")
        check("重放 delete 不复活", st == 404, raw)
        st, _, raw = _request(port2, "GET", "/kv/dead")
        check("重放过期键不复活", st == 404, raw)
        st, _, raw = _request(port2, "GET", "/kv/live")
        check("重放存活键", st == 200 and json.loads(raw)["value"] == "keep", raw)
    finally:
        server2.shutdown()
        server2.server_close()


def test_store_unit():
    """纯 store 级: put/delete/incr 都会追加 WAL(逐操作计数)。"""
    with tempfile.TemporaryDirectory() as d:
        wal = os.path.join(d, "unit.wal")
        store = __import__("kvsvc.store", fromlist=["KvStore"]).KvStore(wal_path=wal)
        store.put("k", 1, None)
        store.incr("k", 2)
        store.delete("k")
        lines = [
            json.loads(x)
            for x in open(wal, "r", encoding="utf-8")
            if x.strip()
        ]
        check(
            "store 三写操作各落一行",
            [x["op"] for x in lines] == ["put", "incr", "delete"],
            repr([x.get("op") for x in lines]),
        )


def run() -> bool:
    print("kvsvc selftest")
    with tempfile.TemporaryDirectory() as d:
        server_mod._STORE = None
        test_http_contract(os.path.join(d, "http.wal"))
        test_concurrency(os.path.join(d, "conc.wal"))
        test_wal_and_replay(os.path.join(d, "replay.wal"))
        test_store_unit()
    print("PASS" if not FAILURES else "FAIL: %d -> %s" % (len(FAILURES), FAILURES))
    return not FAILURES


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
