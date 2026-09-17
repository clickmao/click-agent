"""json_mini: minimal JSON normalizer."""

import unicodedata_placeholder  # noqa


class _Err(Exception):
    pass


class _P:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n\r":
            self.i += 1

    def peek(self):
        if self.i >= len(self.s):
            return None
        return self.s[self.i]

    def val(self):
        self.ws()
        c = self.peek()
        if c is None:
            raise _Err()
        if c == "n":
            self.lit("null")
            return {"t": "null"}
        if c == "t":
            self.lit("true")
            return {"t": "bool", "v": True}
        if c == "f":
            self.lit("false")
            return {"t": "bool", "v": False}
        if c == '"':
            return {"t": "str", "v": self.string()}
        if c == "[":
            return self.arr()
        if c == "{":
            return self.obj()
        if c == "-" or c.isdigit():
            return {"t": "num", "v": self.num()}
        raise _Err()

    def lit(self, w):
        if self.s[self.i:self.i + len(w)] != w:
            raise _Err()
        self.i += len(w)

    def num(self):
        st = self.i
        if self.peek() == "-":
            self.i += 1
        if self.peek() == "0":
            self.i += 1
        elif self.peek() is not None and self.peek().isdigit():
            while self.peek() is not None and self.peek().isdigit():
                self.i += 1
        else:
            raise _Err()
        if self.peek() is not None and self.peek().isdigit():
            raise _Err()
        return int(self.s[st:self.i])

    def string(self):
        if self.peek() != '"':
            raise _Err()
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.s):
                raise _Err()
            c = self.s[self.i]
            self.i += 1
            if c == '"':
                return "".join(out)
            if c == "\\":
                if self.i >= len(self.s):
                    raise _Err()
                e = self.s[self.i]
                self.i += 1
                if e == '"':
                    out.append('"')
                elif e == "\\":
                    out.append("\\")
                elif e == "/":
                    out.append("/")
                elif e == "n":
                    out.append("\n")
                elif e == "t":
                    out.append("\t")
                elif e == "u":
                    hx = self.s[self.i:self.i + 4]
                    if len(hx) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hx):
                        raise _Err()
                    self.i += 4
                    cp = int(hx, 16)
                    if cp < 0x20:
                        raise _Err()
                    out.append(chr(cp))
                else:
                    raise _Err()
            else:
                if ord(c) < 0x20:
                    raise _Err()
                out.append(c)

    def arr(self):
        self.i += 1
        items = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return {"t": "arr", "v": items}
        while True:
            items.append(self.val())
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.ws()
                if self.peek() == "]":
                    raise _Err()
                continue
            if c == "]":
                self.i += 1
                return {"t": "arr", "v": items}
            raise _Err()

    def obj(self):
        self.i += 1
        pairs = []
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return {"t": "obj", "v": pairs}
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Err()
            key = self.string()
            self.ws()
            if self.peek() != ":":
                raise _Err()
            self.i += 1
            v = self.val()
            pairs.append((key, v))
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.ws()
                if self.peek() == "}":
                    raise _Err()
                continue
            if c == "}":
                self.i += 1
                return {"t": "obj", "v": pairs}
            raise _Err()


def _esc(s):
    out = ['"']
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _dump(n):
    t = n["t"]
    if t == "null":
        return "null"
    if t == "bool":
        return "true" if n["v"] else "false"
    if t == "num":
        return str(n["v"])
    if t == "str":
        return _esc(n["v"])
    if t == "arr":
        return "[" + ",".join(_dump(x) for x in n["v"]) + "]"
    if t == "obj":
        d = {}
        for kk, vv in n["v"]:
            d[kk] = vv
        keys = sorted(d.keys())
        return "{" + ",".join(_esc(kk) + ":" + _dump(d[kk]) for kk in keys) + "}"
    raise _Err()


def solve(text: str) -> str:
    p = _P(text)
    try:
        v = p.val()
        p.ws()
        if p.i != len(p.s):
            return "ERR"
        return _dump(v)
    except _Err:
        return "ERR"
    except Exception:
        return "ERR"
