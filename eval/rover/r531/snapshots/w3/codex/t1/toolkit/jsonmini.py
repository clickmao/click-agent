"""A miniature JSON parser and canonical formatter.

solve(text) parses one JSON value and returns the canonical, whitespace-free
rendering, or the single line "ERR" when the input is not valid.
"""

_DIGITS = "0123456789"
_HEX = "0123456789abcdefABCDEF"
_WS = " \t\n\r"
_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class _Fail(Exception):
    pass


class _Obj:
    __slots__ = ("pairs",)

    def __init__(self, pairs):
        self.pairs = pairs


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def fail(self):
        raise _Fail()

    def peek(self):
        return self.s[self.i] if self.i < self.n else ""

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def parse(self):
        self.skip_ws()
        if self.i >= self.n:
            self.fail()
        value = self.parse_value()
        self.skip_ws()
        if self.i != self.n:
            self.fail()
        return value

    def parse_value(self):
        c = self.peek()
        if c == "n":
            self.literal("null")
            return None
        if c == "t":
            self.literal("true")
            return True
        if c == "f":
            self.literal("false")
            return False
        if c == '"':
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c in _DIGITS:
            return self.parse_number()
        self.fail()

    def literal(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            self.fail()
        self.i += len(word)

    def parse_number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.peek() == "0":
            self.i += 1
            if self.peek() in _DIGITS:
                self.fail()
        elif self.peek() in _DIGITS:
            while self.peek() in _DIGITS:
                self.i += 1
        else:
            self.fail()
        nxt = self.peek()
        if nxt != "" and nxt not in " \t\n\r,]}:[":
            self.fail()
        return int(self.s[start:self.i])

    def parse_string(self):
        self.i += 1
        chars = []
        while True:
            if self.i >= self.n:
                self.fail()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    self.fail()
                e = self.s[self.i]
                if e == "u":
                    self.i += 1
                    chars.append(self.read_escaped_char())
                elif e in _ESCAPES:
                    self.i += 1
                    chars.append(_ESCAPES[e])
                else:
                    self.fail()
            elif ord(c) < 0x20:
                self.fail()
            else:
                self.i += 1
                chars.append(c)

    def read_hex4(self):
        if self.i + 4 > self.n:
            self.fail()
        h = self.s[self.i:self.i + 4]
        if any(ch not in _HEX for ch in h):
            self.fail()
        self.i += 4
        return int(h, 16)

    def read_escaped_char(self):
        code = self.read_hex4()
        if 0xD800 <= code <= 0xDBFF:
            if self.s[self.i:self.i + 2] != "\\u":
                self.fail()
            self.i += 2
            low = self.read_hex4()
            if not 0xDC00 <= low <= 0xDFFF:
                self.fail()
            return chr(0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00))
        if 0xDC00 <= code <= 0xDFFF:
            self.fail()
        if code < 0x20:
            self.fail()
        return chr(code)

    def parse_array(self):
        self.i += 1
        items = []
        self.skip_ws()
        if self.peek() == "]":
            self.i += 1
            return items
        while True:
            self.skip_ws()
            items.append(self.parse_value())
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.skip_ws()
                if self.peek() == "]":
                    self.fail()
                continue
            if c == "]":
                self.i += 1
                return items
            self.fail()

    def parse_object(self):
        self.i += 1
        pairs = []
        self.skip_ws()
        if self.peek() == "}":
            self.i += 1
            return _Obj(pairs)
        while True:
            self.skip_ws()
            if self.peek() != '"':
                self.fail()
            key = self.parse_string()
            self.skip_ws()
            if self.peek() != ":":
                self.fail()
            self.i += 1
            self.skip_ws()
            value = self.parse_value()
            pairs.append((key, value))
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.skip_ws()
                if self.peek() == "}":
                    self.fail()
                continue
            if c == "}":
                self.i += 1
                return _Obj(pairs)
            self.fail()


def _to_python(value):
    if isinstance(value, _Obj):
        d = {}
        for k, v in value.pairs:
            d[k] = _to_python(v)
        return d
    if isinstance(value, list):
        return [_to_python(v) for v in value]
    return value


def _encode(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            _encode_string(k) + ":" + _encode(value[k]) for k in sorted(value)
        ) + "}"
    raise _Fail()


def _encode_string(s):
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
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def solve(text: str) -> str:
    try:
        parser = _Parser(text)
        raw = parser.parse()
        value = _to_python(raw)
        return _encode(value)
    except (_Fail, RecursionError):
        return "ERR"
