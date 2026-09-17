"""HTTP 服务入口： python3 -m kvsvc.server --port PORT --wal PATH"""

import argparse
import json
import math
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlsplit

from .store import KVStore, NotIntError

CT = "application/json; charset=utf-8"


class Api:
    """路由与业务逻辑，便于在无网络的情况下单测。"""

    def __init__(self, store: KVStore) -> None:
        self.store = store

    @staticmethod
    def _split(path: str) -> Tuple[str, ...]:
        return tuple(p for p in path.split("/") if p != "")

    def dispatch(self, method: str, raw_path: str,
                 body: bytes) -> Tuple[int, Dict[str, Any]]:
        path = urlsplit(raw_path).path
        parts = self._split(path)
        try:
            if parts == ("stats",) and method == "GET":
                count, expired, uptime_ms = self.store.stats()
                return 200, {"count": count, "expired": expired,
                             "uptime_ms": uptime_ms}
            if len(parts) == 2 and parts[0] == "kv":
                key = unquote(parts[1])
                if method == "PUT":
                    return self._put(key, body)
                if method == "GET":
                    return self._get(key)
                if method == "DELETE":
                    return self._delete(key)
            if len(parts) == 3 and parts[0] == "kv" and parts[2] == "incr" \
                    and method == "POST":
                return self._incr(unquote(parts[1]), body)
            return 404, {"error": "not_found"}
        except NotIntError:
            return 409, {"error": "not_int"}
        except _BadRequest as exc:
            return 400, {"error": exc.code}

    # -------------------------------------------------------------- handlers
    def _put(self, key: str, body: bytes) -> Tuple[int, Dict[str, Any]]:
        data = _parse_body(body)
        if "value" not in data:
            raise _BadRequest("bad_request")
        ttl = data.get("ttl")
        if ttl is not None:
            if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) \
                    or not math.isfinite(ttl) or ttl < 0:
                raise _BadRequest("bad_ttl")
            ttl = float(ttl)
        self.store.put(key, data["value"], ttl)
        if ttl is None:
            expires_in = None
        else:
            expires_in = self.store.remaining(key)
            if expires_in is None:
                expires_in = 0
        return 200, {"key": key, "value": data["value"],
                     "expires_in": expires_in}

    def _get(self, key: str) -> Tuple[int, Dict[str, Any]]:
        if not self.store.exists(key):
            return 404, {"error": "not_found"}
        return 200, {"key": key, "value": self.store.get(key)}

    def _delete(self, key: str) -> Tuple[int, Dict[str, Any]]:
        if not self.store.delete(key):
            return 404, {"error": "not_found"}
        return 200, {"deleted": True}

    def _incr(self, key: str, body: bytes) -> Tuple[int, Dict[str, Any]]:
        data = _parse_body(body)
        by = data.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            raise _BadRequest("bad_by")
        value = self.store.incr(key, by)
        return 200, {"key": key, "value": value}


class _BadRequest(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _parse_body(body: bytes) -> Dict[str, Any]:
    if not body:
        return {}
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise _BadRequest("bad_request")
    if not isinstance(data, dict):
        raise _BadRequest("bad_request")
    return data


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"
    api: Api = None  # type: ignore[assignment]

    # --------------------------------------------------------------- plumbing
    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        return self.rfile.read(length) if length > 0 else b""

    def _respond(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", CT)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method: str) -> None:
        body = self._read_body()
        try:
            status, payload = self.api.dispatch(method, self.path, body)
        except Exception:  # pragma: no cover - 兜底，保证始终返回 JSON
            status, payload = 500, {"error": "internal_error"}
        self._respond(status, payload)

    def do_GET(self) -> None:      # noqa: N802
        self._handle("GET")

    def do_PUT(self) -> None:      # noqa: N802
        self._handle("PUT")

    def do_POST(self) -> None:     # noqa: N802
        self._handle("POST")

    def do_DELETE(self) -> None:   # noqa: N802
        self._handle("DELETE")

    def do_HEAD(self) -> None:     # noqa: N802
        self._handle("HEAD")

    def do_PATCH(self) -> None:    # noqa: N802
        self._handle("PATCH")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._handle("OPTIONS")

    def log_message(self, fmt: str, *args: Any) -> None:  # 静默 STDERR
        return


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", type=str, required=True)
    args = parser.parse_args(argv)

    store = KVStore(wal_path=args.wal)
    store.load_wal()

    handler = type("BoundHandler", (Handler,), {"api": Api(store)})
    httpd = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    httpd.daemon_threads = True

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
    raise SystemExit(main())
