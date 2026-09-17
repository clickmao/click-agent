"""HTTP front-end for the TTL key-value store.

Run with:  python3 -m kvsvc.server --port <int> --wal <path>
"""

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .store import KVStore, NotIntError

CONTENT_TYPE = "application/json; charset=utf-8"
MAX_BODY = 64 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ------------------------------------------------------------- plumbing
    def log_message(self, *args):  # keep stdout/stderr clean for the harness
        pass

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self):
        self._send(404, {"error": "not_found"})

    def _read_json(self):
        length = self.headers.get("Content-Length")
        if not length:
            return {}
        try:
            raw = self.rfile.read(int(length))
        except (ValueError, OSError):
            return {}
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return data

    def _split_path(self):
        path = urlparse(self.path).path
        parts = [unquote(p) for p in path.split("/") if p != ""]
        return parts

    # --------------------------------------------------------------- routes
    def do_GET(self):
        with self.server.lock:
            parts = self._split_path()
            if parts == ["stats"]:
                return self._send(200, self.server.store.stats())
            if len(parts) == 2 and parts[0] == "kv":
                found, value = self.server.store.get(parts[1])
                if not found:
                    return self._not_found()
                return self._send(200, {"key": parts[1], "value": value})
            return self._not_found()

    def do_PUT(self):
        with self.server.lock:
            parts = self._split_path()
            if len(parts) != 2 or parts[0] != "kv":
                return self._not_found()
            body = self._read_json()
            if not isinstance(body, dict) or "value" not in body:
                return self._send(400, {"error": "bad_request"})
            ttl = body.get("ttl")
            if ttl is not None:
                if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
                    return self._send(400, {"error": "bad_request"})
                ttl = float(ttl)
            self.server.store.put(parts[1], body["value"], ttl)
            remaining = ttl
            return self._send(
                200,
                {"key": parts[1], "value": body["value"], "expires_in": remaining},
            )

    def do_DELETE(self):
        with self.server.lock:
            parts = self._split_path()
            if len(parts) != 2 or parts[0] != "kv":
                return self._not_found()
            if self.server.store.delete(parts[1]):
                return self._send(200, {"deleted": True})
            return self._not_found()

    def do_POST(self):
        with self.server.lock:
            parts = self._split_path()
            if len(parts) != 3 or parts[0] != "kv" or parts[2] != "incr":
                return self._not_found()
            body = self._read_json()
            if body is None:
                return self._send(400, {"error": "bad_request"})
            if not isinstance(body, dict):
                return self._send(400, {"error": "bad_request"})
            by = body.get("by", 1)
            if isinstance(by, bool) or not isinstance(by, int):
                return self._send(400, {"error": "bad_request"})
            try:
                value = self.server.store.incr(parts[1], by)
            except NotIntError:
                return self._send(409, {"error": "not_int"})
            return self._send(200, {"key": parts[1], "value": value})

    def _other(self):
        self._not_found()

    do_HEAD = do_OPTIONS = do_PATCH = do_TRACE = _other


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, store):
        super().__init__(address, Handler)
        self.store = store
        self.lock = threading.Lock()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    store = KVStore(args.wal)
    httpd = Server((args.host, args.port), store)
    sys.stdout.write("READY\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
