"""json_mini: parse a JSON value, emit canonical minimal text.

stdin: whole text = one JSON value (leading/trailing whitespace allowed).

supported: null / true / false / decimal integer (optional '-', no leading
zeros, "-0" accepted and normalized to 0) / string / array / object
(string keys). strings only allow standard escapes: \\" \\\\ \\/ \\n \\t \\uXXXX
(decoded code point must be >= 0x20). duplicate object keys: last wins.
output: no whitespace; strings re-escape only  quote, backslash, newline,
tab; other characters verbatim; object keys sorted by code point.
illegal input (syntax error, trailing content, bad escape, bad number,
empty input, decode error) -> single line "ERR".
"""

ERR = "ERR"

WS = " \t\n\r"


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        v = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            raise _Bad()
        return _emit(v)
    except _Bad:
        return ERR


class _Bad(Exception):
    pass


class _Parser:
    def __init__(self, s: str):
        self.s = s
        self.n = len(s)
        self.i = 0

    def skip_ws(self) -> None:
        while self.i < self.n and self.s[self.i] in WS:
            self.i += 1

    def peek(self) -> str:
        if self.i >= self.n:
            raise _Bad()
        return self.s[self.i]

    def parse_value(self):
        self.skip_ws()
        c = self.peek()
        if c == "n":
            return self.lit("null", None)
        if c == "t":
            return self.lit("true", True)
        if c == "f":
            return self.lit("false", False)
        if c == '"':
            return ("s", self.parse_string())
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Bad()

    def lit(self, word: str, val):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Bad()
        self.i += len(word)
        return ("lit", val)

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.i >= self.n:
                raise _Bad()
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Bad()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Bad()
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        raw = self.s[start:self.i]
        try:
            val = int(raw)
        except ValueError:
            raise _Bad()
        return ("num", val)

    def parse_string(self) -> str:
        if self.s[self.i] != '"':
            raise _Bad()
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise _Bad()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Bad()
                e = self.s[self.i]
                self.i += 1
                if e == '"':
                    buf.append('"')
                elif e == "\\":
                    buf.append("\\")
                elif e == "/":
                    buf.append("/")
                elif e == "n":
                    buf.append("\n")
                elif e == "t":
                    buf.append("\t")
                elif e == "u":
                    cp = self.parse_hex4()
                    if cp < 0x20:
                        raise _Bad()
                    buf.append(chr(cp))
                else:
                    raise _Bad()
            elif ord(c) < 0x20:
                raise _Bad()
            else:
                buf.append(c)
                self.i += 1

    def parse_hex4(self) -> int:
        if self.i + 4 > self.n:
            raise _Bad()
        h = self.s[self.i:self.i + 4]
        for ch in h:
            if ch not in "0123456789abcdefABCDEF":
                raise _Bad()
        self.i += 4
        return int(h, 16)

    def parse_array(self):
        self.i += 1
        items = []
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return ("arr", items)
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return ("arr", items)
            raise _Bad()

    def parse_object(self):
        self.i += 1
        d = {}
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return ("obj", d)
        while True:
            self.skip_ws()
            key = self.parse_string()
            self.skip_ws()
            if self.peek() != ":":
                raise _Bad()
            self.i += 1
            val = self.parse_value()
            d[key] = val
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return ("obj", d)
            raise _Bad()


def _emit(node) -> str:
    tag, val = node
    if tag == "lit":
        return "null" if val is None else ("true" if val else "false")
    if tag == "num":
        return str(val)
    if tag == "s":
        out = ['"']
        for ch in val:
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
    if tag == "arr":
        return "[" + ",".join(_emit(x) for x in val) + "]"
    if tag == "obj":
        keys = sorted(val.keys())
        return "{" + ",".join(_emit(("s", k)) + ":" + _emit(val[k]) for k in keys) + "}"
    raise _Bad()
