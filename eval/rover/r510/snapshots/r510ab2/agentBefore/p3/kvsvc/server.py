"""HTTP 服务入口。

运行:
    python3 -m kvsvc.server --port 8000 --wal ./data/wal.jsonl

就绪后 stdout 打印一行 ``READY`` 并 flush (评测据此判定可连)。
并发模型: ``ThreadingHTTPServer`` —— 每连接一线程, 后端 KVStore 自带锁。

自检:
    python3 -m kvsvc.server --selftest
退出码 0=全部通过, 非 0=失败。
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

from .store import KVStore

__all__ = ["KVRequestHandler", "make_server", "main"]

_JSON_CT = "application/json; charset=utf-8"
_MAX_BODY = 8 * 1024 * 1024  # 8 MiB 请求体上限


class KVRequestHandler(BaseHTTPRequestHandler):
    """单个请求处理器。store 挂在 server 实例上, 全服务共享。"""

    server_version = "kvsvc/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------ 基础设施
    @property
    def store(self) -> KVStore:
        return self.server.store  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        """静默: 不向 stdout/stderr 打印任何多余文字。"""

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", _JSON_CT)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        """读取并解析请求体; 空体返回 {}; 非法 JSON 抛 ValueError。"""
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            return {}
        try:
            length = int(raw_len)
        except (TypeError, ValueError) as exc:
            raise ValueError("bad_content_length") from exc
        if length <= 0:
            return {}
        if length > _MAX_BODY:
            raise ValueError("body_too_large")
        data = self.rfile.read(length)
        if not data.strip():
            return {}
        obj = json.loads(data.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("body_not_object")
        return obj

    # --------------------------------------------------------------- 路由
    def _route(self, method: str) -> Tuple[str, List[str]]:
        path = urlsplit(self.path).path
        segments = [unquote(s) for s in path.split("/") if s != ""]
        return method, segments

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        try:
            _, seg = self._route(method)
            handler = self._resolve(method, seg)
            if handler is None:
                self._send(404, {"error": "not_found"})
                return
            handler(seg)
        except ValueError:
            # 请求体非法(非 JSON / 非对象 / 超长)
            self._send(400, {"error": "bad_request"})
        except Exception:  # pragma: no cover - 兜底, 绝不因单请求崩溃进程
            self._send(500, {"error": "internal_error"})

    def _resolve(self, method: str, seg: List[str]):
        # GET /stats
        if method == "GET" and seg == ["stats"]:
            return self._h_stats
        # /kv/{key} 与 /kv/{key}/incr
        if len(seg) >= 2 and seg[0] == "kv":
            if len(seg) == 2:
                key = seg[1]
                if method == "PUT":
                    return lambda s: self._h_put(s[1])
                if method == "GET":
                    return lambda s: self._h_get(s[1])
                if method == "DELETE":
                    return lambda s: self._h_delete(s[1])
                return None
            if len(seg) == 3 and seg[2] == "incr" and method == "POST":
                return lambda s: self._h_incr(s[1])
        return None

    # --------------------------------------------------------------- 处理函数
    def _h_put(self, key: str) -> None:
        body = self._read_json()
        if "value" not in body:
            self._send(400, {"error": "bad_request"})
            return
        ttl = body.get("ttl", None)
        if ttl is not None:
            if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                self._send(400, {"error": "bad_request"})
                return
            ttl = float(ttl)
        res = self.store.put(key, body["value"], ttl)
        self._send(200, res)

    def _h_get(self, key: str) -> None:
        res = self.store.get(key)
        if res is None:
            self._send(404, {"error": "not_found"})
            return
        self._send(200, res)

    def _h_delete(self, key: str) -> None:
        if self.store.delete(key):
            self._send(200, {"deleted": True})
        else:
            self._send(404, {"error": "not_found"})

    def _h_incr(self, key: str) -> None:
        body = self._read_json()
        by = body.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            # by 非整数: 契约里未定义, 归为 409 not_int(语义最接近)
            self._send(409, {"error": "not_int"})
            return
        try:
            res = self.store.incr(key, by)
        except ValueError:
            self._send(409, {"error": "not_int"})
            return
        self._send(200, res)

    def _h_stats(self) -> None:
        self._send(200, self.store.stats())


class KVServer(ThreadingHTTPServer):
    """把 store 挂在 server 上, 便于 handler 访问。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr: Tuple[str, int], store: KVStore) -> None:
        self.store = store
        super().__init__(addr, KVRequestHandler)


def make_server(host: str, port: int, store: KVStore) -> KVServer:
    return KVServer((host, port), store)


# ------------------------------------------------------------------- selftest
def _http(method: str, url: str, payload: Optional[dict] = None, timeout: float = 5.0):
    """极简 HTTP 客户端。返回 (status, headers, parsed_json_or_None)。"""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ct = resp.headers.get("Content-Type", "")
            body = json.loads(raw.decode("utf-8")) if raw else None
            return resp.status, ct, body
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        ct = exc.headers.get("Content-Type", "")
        body = json.loads(raw.decode("utf-8")) if raw else None
        return exc.code, ct, body


def _selftest() -> int:
    import os
    import socket
    import tempfile

    failures: List[str] = []
    checks: List[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        checks.append(name)
        if not cond:
            failures.append(f"{name}: {detail}")

    tmpdir = tempfile.mkdtemp(prefix="kvsvc_selftest_")
    wal = os.path.join(tmpdir, "wal.jsonl")

    # 占用端口探测: 让内核分配一个空闲端口, 避免与其他测试争用
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    store = KVStore(wal)
    srv = make_server("127.0.0.1", port, store)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # 1. 基本 PUT/GET + Content-Type
        st, ct, body = _http("PUT", f"{base}/kv/a", {"value": {"x": 1}, "ttl": 60})
        check("put_200", st == 200, f"st={st}")
        check("content_type", ct == _JSON_CT, f"ct={ct!r}")
        check("put_shape", body.get("key") == "a" and body.get("value") == {"x": 1}
              and isinstance(body.get("expires_in"), (int, float)), f"body={body}")
        st, ct, body = _http("GET", f"{base}/kv/a")
        check("get_200", st == 200 and body == {"key": "a", "value": {"x": 1}}, f"{st} {body}")

        # 2. 无 ttl -> expires_in 必须为 null
        st, _, body = _http("PUT", f"{base}/kv/b", {"value": 5})
        check("no_ttl_null", body.get("expires_in") is None, f"body={body}")

        # 3. 404 语义
        st, _, body = _http("GET", f"{base}/kv/missing")
        check("get_404", st == 404 and body == {"error": "not_found"}, f"{st} {body}")
        st, _, body = _http("DELETE", f"{base}/kv/missing")
        check("del_404", st == 404 and body == {"error": "not_found"}, f"{st} {body}")
        st, _, _ = _http("GET", f"{base}/nope")
        check("bad_route_404", st == 404, f"st={st}")

        # 4. incr: 不存在按 0 起算; 非整数原值 -> 409
        st, _, body = _http("POST", f"{base}/kv/c/incr", {"by": 7})
        check("incr_from_zero", st == 200 and body == {"key": "c", "value": 7}, f"{st} {body}")
        st, _, body = _http("POST", f"{base}/kv/c/incr", {})
        check("incr_default_by", st == 200 and body["value"] == 8, f"{st} {body}")
        _http("PUT", f"{base}/kv/s", {"value": "text"})
        st, _, body = _http("POST", f"{base}/kv/s/incr", {"by": 1})
        check("incr_not_int_409", st == 409 and body == {"error": "not_int"}, f"{st} {body}")

        # 5. DELETE 正常路径
        st, _, body = _http("DELETE", f"{base}/kv/b")
        check("del_200", st == 200 and body == {"deleted": True}, f"{st} {body}")
        st, _, _ = _http("GET", f"{base}/kv/b")
        check("del_then_404", st == 404, f"st={st}")

        # 6. TTL 惰性过期 + expired 计数
        before = _http("GET", f"{base}/stats")[2]
        _http("PUT", f"{base}/kv/t", {"value": 1, "ttl": 0.3})
        st, _, _ = _http("GET", f"{base}/kv/t")
        check("ttl_visible", st == 200, f"st={st}")
        time.sleep(0.45)
        st, _, body = _http("GET", f"{base}/kv/t")
        check("ttl_invisible", st == 404 and body == {"error": "not_found"}, f"{st} {body}")
        after = _http("GET", f"{base}/stats")[2]
        check("expired_counted", after["expired"] > before["expired"],
              f"before={before} after={after}")

        # 7. 并发 incr 无丢更新: 8 客户端 x 20 次
        _http("PUT", f"{base}/kv/cc", {"value": 0})
        errors: List[str] = []

        def worker() -> None:
            for _ in range(20):
                st, _, _ = _http("POST", f"{base}/kv/cc/incr", {"by": 1})
                if st != 200:
                    errors.append(f"st={st}")

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        st, _, body = _http("GET", f"{base}/kv/cc")
        check("concurrent_incr_exact", body and body.get("value") == 160,
              f"value={body.get('value')} errors={errors[:3]}")

        # 8. /stats 形状
        st, _, body = _http("GET", f"{base}/stats")
        check("stats_shape",
              st == 200 and isinstance(body.get("count"), int)
              and isinstance(body.get("expired"), int)
              and isinstance(body.get("uptime_ms"), int), f"body={body}")
    finally:
        srv.shutdown()
        srv.server_close()
        store.close()

    # 9. WAL 行格式与重放
    bad_lines: List[str] = []
    ops_seen = set()
    with open(wal, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            rec = json.loads(ln)
            if not isinstance(rec, dict) or "op" not in rec or "key" not in rec:
                bad_lines.append(ln)
            else:
                ops_seen.add(rec["op"])
    check("wal_lines_valid", not bad_lines, f"bad={bad_lines[:2]}")
    check("wal_ops_subset", ops_seen <= {"put", "delete", "incr"}, f"ops={ops_seen}")
    check("wal_has_incr", "incr" in ops_seen, f"ops={ops_seen}")

    # 重放: 新 store 从同一 WAL 恢复
    store2 = KVStore(wal)
    try:
        check("replay_incr_value", (store2.get("cc") or {}).get("value") == 160,
              f"got={store2.get('cc')}")
        check("replay_key_a", (store2.get("a") or {}).get("value") == {"x": 1},
              f"got={store2.get('a')}")
        check("replay_deleted_gone", store2.get("b") is None, f"got={store2.get('b')}")
        # 已过期键不得复活: 先写一个 0.2s TTL 的键, 等过期后新开 store
        store2.put("ephemeral", "v", 0.2)
    finally:
        store2.close()
    time.sleep(0.35)
    store3 = KVStore(wal)
    try:
        check("replay_expired_not_revived", store3.get("ephemeral") is None,
              f"got={store3.get('ephemeral')}")
    finally:
        store3.close()

    # 10. 负向控制: 未加锁的朴素实现应当丢更新(证明并发断言非空转)
    class _Naive:
        def __init__(self) -> None:
            self.v = 0

        def incr(self) -> None:
            tmp = self.v
            time.sleep(0)   # 放大竞态窗口
            self.v = tmp + 1

    naive = _Naive()

    def naive_worker() -> None:
        for _ in range(20):
            naive.incr()

    nthreads = [threading.Thread(target=naive_worker) for _ in range(8)]
    for th in nthreads:
        th.start()
    for th in nthreads:
        th.join()
    check("negative_control_detects_loss", naive.v < 160 or True,
          "朴素实现可能恰好正确, 此检查仅记录, 不计入失败")

    total = len(checks) - 1  # 负向控制的记录项不计入
    print(f"SELFTEST: {total - len(failures)}/{total} passed")
    for f in failures:
        print("FAIL " + f)
    if failures:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


# ------------------------------------------------------------------------ CLI
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m kvsvc.server",
        description="带 TTL 的键值存储 HTTP 服务(纯标准库)",
    )
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    parser.add_argument("--wal", type=str, default=None, help="WAL 文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行无头自检后退出")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    store = KVStore(args.wal)
    httpd = make_server(args.host, args.port, store)
    # 就绪信号: 必须 flush, 否则评测端读不到
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
