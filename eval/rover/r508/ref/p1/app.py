#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 P1 参考解 (oracle): 待办 HTTP 服务 —— 判据器正控。
契约与 taskset-r508.json 中 p1 的 prompt 逐条对应 (标准库 only)。"""
from __future__ import annotations
import argparse, json, re, signal, sqlite3, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = {"path": ""}


def _db():
    c = sqlite3.connect(DB["path"])
    c.execute("CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0)")
    return c


def _send(h, code, obj):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n > 0 else b""
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return None

    def _row(self, tid):
        c = _db()
        try:
            r = c.execute("SELECT id,text,done FROM todos WHERE id=?", (tid,)).fetchone()
        finally:
            c.close()
        return None if r is None else {"id": r[0], "text": r[1], "done": bool(r[2])}

    def do_GET(self):
        m = re.fullmatch(r"/todos/(\d+)", self.path)
        if self.path == "/todos":
            c = _db()
            try:
                rows = c.execute("SELECT id,text,done FROM todos ORDER BY id ASC").fetchall()
            finally:
                c.close()
            return _send(self, 200, {"todos": [{"id": r[0], "text": r[1], "done": bool(r[2])} for r in rows]})
        if m:
            row = self._row(int(m.group(1)))
            return _send(self, 200, row) if row else _send(self, 404, {"error": "not_found"})
        return _send(self, 404, {"error": "not_found"})

    def do_POST(self):
        m = re.fullmatch(r"/todos/(\d+)/done", self.path)
        if self.path == "/todos":
            b = self._body()
            text = (b or {}).get("text") if isinstance(b, dict) else None
            if not isinstance(text, str) or not text.strip():
                return _send(self, 400, {"error": "bad_request"})
            c = _db()
            try:
                cur = c.execute("INSERT INTO todos(text,done) VALUES(?,0)", (text,))
                c.commit()
                tid = cur.lastrowid
            finally:
                c.close()
            return _send(self, 201, {"id": tid, "text": text, "done": False})
        if m:
            tid = int(m.group(1))
            if self._row(tid) is None:
                return _send(self, 404, {"error": "not_found"})
            c = _db()
            try:
                c.execute("UPDATE todos SET done=1 WHERE id=?", (tid,))
                c.commit()
            finally:
                c.close()
            return _send(self, 200, self._row(tid))
        return _send(self, 404, {"error": "not_found"})

    def do_DELETE(self):
        m = re.fullmatch(r"/todos/(\d+)", self.path)
        if not m:
            return _send(self, 404, {"error": "not_found"})
        tid = int(m.group(1))
        if self._row(tid) is None:
            return _send(self, 404, {"error": "not_found"})
        c = _db()
        try:
            c.execute("DELETE FROM todos WHERE id=?", (tid,))
            c.commit()
        finally:
            c.close()
        return _send(self, 200, {"deleted": True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--db", required=True)
    a = ap.parse_args()
    DB["path"] = a.db
    _db().close()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print("READY", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
