"""jsonmini: minimal JSON parser + canonical serializer.

Accepts exactly one JSON value (surrounded by optional whitespace).
Supported: null, true, false, decimal integers (optional '-' sign, no leading
zeros, "-0" normalizes to 0), strings, arrays, objects (string keys).

Strings allow only the six standard escapes: \\" \\\\ \\/ \\n \\t \\uXXXX.
Decoded code points from \\uXXXX must be >= 0x20.

Objects allow duplicate keys; later occurrences override earlier ones.

Output: canonical text with no whitespace at all. Strings re-escape only
quote, backslash, newline and tab; every other character is emitted verbatim.
Object keys are sorted by Unicode code point.

Any illegal input (syntax error, trailing content, bad escape, bad number,
empty input) yields a single line "ERR".
"""


class _Err(Exception):
    pass


_WS = " \t\n\r"


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def parse_value(self):
        self.skip_ws()
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == '"':
            return self.parse_string()
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == "t":
            return self.expect_lit("true", True)
        if c == "f":
            return self.expect_lit("false", False)
        if c == "n":
            return self.expect_lit("null", None)
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Err()

    def expect_lit(self, word, value):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return value
        raise _Err()

    def parse_number(self):
        start = self.i
        if self.i < self.n and self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Err()
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        return int(self.s[start:self.i])

    def parse_string(self):
        # assumes current char is '"'
        self.i += 1
        out = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
                e = self.s[self.i]
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
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    out.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err()
                self.i += 1
                continue
            if ord(c) < 0x20:
                raise _Err()
            out.append(c)
            self.i += 1

    def parse_array(self):
        self.i += 1  # '['
        self.skip_ws()
        items = []
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            raise _Err()

    def parse_object(self):
        self.i += 1  # '{'
        self.skip_ws()
        obj = {}
        order = []
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            val = self.parse_value()
            if key not in obj:
                order.append(key)
            obj[key] = val
            self.skip_ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _Err()


def _escape_string(s):
    out = []
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
    return '"' + "".join(out) + '"'


def _serialize(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _escape_string(v)
    if isinstance(v, list):
        return "[" + ",".join(_serialize(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(_escape_string(k) + ":" + _serialize(v[k]) for k in keys) + "}"
    raise _Err()


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        val = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            raise _Err()
    except _Err:
        return "ERR"
    except (ValueError, IndexError):
        return "ERR"
    try:
        return _serialize(val)
    except _Err:
        return "ERR"
