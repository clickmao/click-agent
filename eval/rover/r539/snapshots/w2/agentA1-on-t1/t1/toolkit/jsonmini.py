# -*- coding: utf-8 -*-
"""jsonmini subcommand: strict JSON-lite normalizer.

solve(text) -> canonical text with no whitespace; "ERR" on invalid input.

Grammar:
  value  = null | true | false | int | string | array | object
  int    = optional minus, then digits (no leading zeros; minus-zero -> 0)
  string = double-quoted, only standard escapes: quote, backslash, slash,
           n, t, and uXXXX (decoded code point must be >= 0x20)
  object = braces, keys are strings; duplicate keys: later overrides earlier
Output:
  strings re-escape quote, backslash, newline, tab; other chars as-is
  object keys sorted by Unicode code point ascending
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.n = len(s)
        self.i = 0

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ""

    def expect(self, ch):
        if self.peek() != ch:
            raise _Err("expected " + ch)
        self.i += 1

    def parse(self):
        self.ws()
        if self.i >= self.n:
            raise _Err("empty input")
        v = self.value()
        self.ws()
        if self.i != self.n:
            raise _Err("trailing content")
        return v

    def value(self):
        c = self.peek()
        if c == "":
            raise _Err("eof")
        if c == '"':
            return ("str", self.string())
        if c == "{":
            return ("obj", self.obj())
        if c == "[":
            return ("arr", self.arr())
        if c == "t":
            self.lit("true")
            return ("bool", True)
        if c == "f":
            self.lit("false")
            return ("bool", False)
        if c == "n":
            self.lit("null")
            return ("null", None)
        if c == "-" or c.isdigit():
            return ("int", self.integer())
        raise _Err("bad value")

    def lit(self, word):
        if self.s.startswith(word, self.i):
            self.i += len(word)
        else:
            raise _Err("bad literal")

    def integer(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.peek() == "" or not self.peek().isdigit():
            raise _Err("bad int")
        if self.peek() == "0":
            self.i += 1
            if self.peek().isdigit():
                raise _Err("leading zero")
        else:
            while self.peek().isdigit():
                self.i += 1
        tok = self.s[start:self.i]
        try:
            val = int(tok)
        except ValueError:
            raise _Err("bad int")
        return val

    def string(self):
        self.expect('"')
        out = []
        while True:
            if self.i >= self.n:
                raise _Err("unterminated string")
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err("bad escape")
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
                    if self.i + 4 > self.n:
                        raise _Err("bad u escape")
                    hexs = self.s[self.i:self.i + 4]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        raise _Err("bad u escape")
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err("control code")
                    out.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err("bad escape")
            elif ord(c) < 0x20:
                raise _Err("raw control")
            else:
                out.append(c)
                self.i += 1

    def arr(self):
        self.expect("[")
        items = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return items
        while True:
            self.ws()
            items.append(self.value())
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            raise _Err("bad array")

    def obj(self):
        self.expect("{")
        pairs = {}
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return pairs
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Err("bad key")
            key = self.string()
            self.ws()
            self.expect(":")
            self.ws()
            pairs[key] = self.value()
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return pairs
            raise _Err("bad object")


def _render(v):
    kind = v[0]
    if kind == "null":
        return "null"
    if kind == "bool":
        return "true" if v[1] else "false"
    if kind == "int":
        return str(v[1])
    if kind == "str":
        return _render_str(v[1])
    if kind == "arr":
        return "[" + ",".join(_render(x) for x in v[1]) + "]"
    if kind == "obj":
        pairs = v[1]
        keys = sorted(pairs.keys())
        return "{" + ",".join(_render_str(k) + ":" + _render(pairs[k]) for k in keys) + "}"
    raise _Err("bad node")


def _render_str(s):
    out = ['"']
    for c in s:
        if c == '"':
            out.append('\\"')
        elif c == "\\":
            out.append("\\\\")
        elif c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        else:
            out.append(c)
    out.append('"')
    return "".join(out)


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        v = p.parse()
        return _render(v)
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
    except Exception:
        return "ERR"
