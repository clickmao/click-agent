"""HTTP front-end for the key/value store.

Run with::

    python3 -m kvsvc.server --port 8080 --wal /tmp/kv.wal
"""

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .store import Store

CONTENT_TYPE = "application/json; charset=utf-8"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "kvsvc/1.0"

    # ----------------------------------------------------------- low level
    def log_message(self, fmt, *args):
        # Keep stderr quiet-ish but still informative.
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", CONTENT_TYPE)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self):
        self._send(404, {"error": "not_found"})

    def _read_body(self):
        length = self.headers.get("Content-Length")
        if length is None:
            return b""
        try:
            length = int(length)
        except ValueError:
            return b""
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _read_json(self):
        raw = self._read_body()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    # ------------------------------------------------------------- routing
    def _route(self, method):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        parts = [p for p in path.split("/") if p != ""]

        if method == "GET" and parts == ["stats"]:
            self._send(200, self.server.store.stats())
            return

        if len(parts) == 2 and parts[0] == "kv":
            key = parts[1]
            if method == "PUT":
                self._handle_put(key)
                return
            if method == "GET":
                self._handle_get(key)
                return
            if method == "DELETE":
                self._handle_delete(key)
                return

        if len(parts) == 3 and parts[0] == "kv" and parts[2] == "incr" and method == "POST":
            self._handle_incr(parts[1])
            return

        self._not_found()

    def do_GET(self):
        self._route("GET")

    def do_PUT(self):
        self._route("PUT")

    def do_POST(self):
        self._route("POST")

    def do_DELETE(self):
        self._route("DELETE")

    def do_HEAD(self):
        self._not_found()

    def do_PATCH(self):
        self._not_found()

    def do_OPTIONS(self):
        self._not_found()

    # ---------------------------------------------------------- operations
    def _handle_put(self, key):
        payload = self._read_json()
        if payload is None or "value" not in payload:
            self._send(400, {"error": "bad_request"})
            return
        ttl = payload.get("ttl", None)
        if ttl is not None:
            try:
                ttl = float(ttl)
            except (TypeError, ValueError):
                self._send(400, {"error": "bad_request"})
                return
            if ttl < 0:
                self._send(400, {"error": "bad_request"})
                return
        result = self.server.store.put(key, payload["value"], ttl)
        self._send(200, result)

    def _handle_get(self, key):
        result = self.server.store.get(key)
        if result is None:
            self._not_found()
        else:
            self._send(200, result)

    def _handle_delete(self, key):
        if self.server.store.delete(key):
            self._send(200, {"deleted": True})
        else:
            self._not_found()

    def _handle_incr(self, key):
        payload = self._read_json()
        if payload is None:
            self._send(400, {"error": "bad_request"})
            return
        by = payload.get("by", 1)
        if isinstance(by, bool) or not isinstance(by, int):
            self._send(400, {"error": "bad_request"})
            return
        result = self.server.store.incr(key, by)
        if result is None:
            self._send(409, {"error": "not_int"})
        else:
            self._send(200, result)


class KVServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def build_server(port, wal_path):
    store = Store(wal_path)
    server = KVServer(("0.0.0.0", port), Handler)
    server.store = store
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kvsvc.server")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--wal", required=True)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args(argv)

    server = build_server(args.port, args.wal)
    try:
        sys.stdout.write("READY\n")
        sys.stdout.flush()
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
