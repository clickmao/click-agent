"""Subcommand ``jsonmini``: minimal strict JSON parser and canonical printer."""

_ERR = "ERR"
_WS = " \t\n\r"
_DIGITS = "0123456789"
_HEX = "0123456789abcdefABCDEF"

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


class _Err(Exception):
    """Any invalid input, mapped to a single ``ERR`` line."""


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def error(self):
        raise _Err

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def parse_value(self):
        self.skip_ws()
        if self.i >= self.n:
            self.error()
        ch = self.s[self.i]
        if ch == "{":
            return self.parse_object()
        if ch == "[":
            return self.parse_array()
        if ch == '"':
            return self.parse_string()
        if self.s.startswith("true", self.i):
            self.i += 4
            return True
        if self.s.startswith("false", self.i):
            self.i += 5
            return False
        if self.s.startswith("null", self.i):
            self.i += 4
            return None
        if ch == "-" or ch in _DIGITS:
            return self.parse_number()
        self.error()

    def parse_string(self):
        if self.s[self.i] != '"':
            self.error()
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                self.error()
            ch = self.s[self.i]
            if ch == '"':
                self.i += 1
                return "".join(buf)
            if ch == "\\":
                self.i += 1
                if self.i >= self.n:
                    self.error()
                esc = self.s[self.i]
                if esc == "u":
                    self.i += 1
                    if self.i + 4 > self.n:
                        self.error()
                    hex4 = self.s[self.i:self.i + 4]
                    if any(c not in _HEX for c in hex4):
                        self.error()
                    cp = int(hex4, 16)
                    self.i += 4
                    if cp < 0x20:
                        self.error()
                    buf.append(chr(cp))
                elif esc in _ESCAPES:
                    buf.append(_ESCAPES[esc])
                    self.i += 1
                else:
                    self.error()
            elif ord(ch) < 0x20:
                self.error()
            else:
                buf.append(ch)
                self.i += 1

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or self.s[self.i] not in _DIGITS:
            self.error()
        if self.s[self.i] == "0":
            self.i += 1
        else:
            self.i += 1
            while self.i < self.n and self.s[self.i] in _DIGITS:
                self.i += 1
        if self.i < self.n and self.s[self.i] in ".eE":
            self.error()
        raw = self.s[start:self.i]
        try:
            return int(raw)
        except ValueError:
            self.error()

    def parse_array(self):
        self.i += 1  # consume '['
        self.skip_ws()
        items = []
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            if self.i >= self.n:
                self.error()
            ch = self.s[self.i]
            if ch == ",":
                self.i += 1
                continue
            if ch == "]":
                self.i += 1
                return items
            self.error()

    def parse_object(self):
        self.i += 1  # consume '{'
        self.skip_ws()
        pairs = {}
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                self.error()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != ":":
                self.error()
            self.i += 1
            pairs[key] = self.parse_value()
            self.skip_ws()
            if self.i >= self.n:
                self.error()
            ch = self.s[self.i]
            if ch == ",":
                self.i += 1
                continue
            if ch == "}":
                self.i += 1
                return pairs
            self.error()

    def parse_document(self):
        value = self.parse_value()
        self.skip_ws()
        if self.i != self.n:
            self.error()
        return value


def _emit_string(s):
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


def _emit(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _emit_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_emit(item) for item in value) + "]"
    out = ["{"]
    keys = sorted(value.keys())
    out.append(",".join(_emit_string(k) + ":" + _emit(value[k]) for k in keys))
    out.append("}")
    return "".join(out)


def solve(text):
    try:
        value = _Parser(text).parse_document()
    except _Err:
        return _ERR
    return _emit(value)
