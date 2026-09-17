"""Subcommand module for `json_mini`: strict JSON parser + canonical writer."""

_WS = " \t\n\r"
_HEX = "0123456789abcdefABCDEF"
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class _Error(Exception):
    pass


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def parse(self):
        self._skip_ws()
        value = self._value()
        self._skip_ws()
        if self.i != self.n:
            raise _Error()
        return value

    def _skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def _value(self):
        if self.i >= self.n:
            raise _Error()
        c = self.s[self.i]
        if c == "{":
            return self._object()
        if c == "[":
            return self._array()
        if c == '"':
            return self._string()
        if c == "t":
            return self._literal("true", True)
        if c == "f":
            return self._literal("false", False)
        if c == "n":
            return self._literal("null", None)
        if c == "-" or c.isdigit():
            return self._number()
        raise _Error()

    def _literal(self, word, value):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Error()
        self.i += len(word)
        return value

    def _number(self):
        start = self.i
        neg = False
        if self.s[self.i] == "-":
            neg = True
            self.i += 1
        if self.i >= self.n:
            raise _Error()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Error()
        elif self.s[self.i].isdigit():
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        else:
            raise _Error()
        digits = self.s[start:self.i]
        return int(digits)

    def _string(self):
        if self.s[self.i] != '"':
            raise _Error()
        self.i += 1
        chars = []
        while True:
            if self.i >= self.n:
                raise _Error()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Error()
                e = self.s[self.i]
                if e == "u":
                    self.i += 1
                    code = self._hex4()
                    chars.append(chr(code))
                elif e in _ESCAPES:
                    chars.append(_ESCAPES[e])
                    self.i += 1
                else:
                    raise _Error()
            else:
                if ord(c) < 0x20:
                    raise _Error()
                chars.append(c)
                self.i += 1

    def _hex4(self):
        if self.i + 4 > self.n:
            raise _Error()
        h = self.s[self.i:self.i + 4]
        for ch in h:
            if ch not in _HEX:
                raise _Error()
        self.i += 4
        return int(h, 16)

    def _array(self):
        self.i += 1
        self._skip_ws()
        items = []
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            self._skip_ws()
            items.append(self._value())
            self._skip_ws()
            if self.i >= self.n:
                raise _Error()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                self._skip_ws()
                if self.i < self.n and self.s[self.i] == "]":
                    raise _Error()
                continue
            if c == "]":
                self.i += 1
                return items
            raise _Error()

    def _object(self):
        self.i += 1
        self._skip_ws()
        pairs = {}
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self._skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Error()
            key = self._string()
            self._skip_ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Error()
            self.i += 1
            self._skip_ws()
            value = self._value()
            pairs[key] = value
            self._skip_ws()
            if self.i >= self.n:
                raise _Error()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                self._skip_ws()
                if self.i < self.n and self.s[self.i] == "}":
                    raise _Error()
                continue
            if c == "}":
                self.i += 1
                return pairs
            raise _Error()


def _write(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _write_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_write(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return "{" + ",".join(_write_string(k) + ":" + _write(value[k]) for k in keys) + "}"
    raise _Error()


def _write_string(s):
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
        value = _Parser(text).parse()
    except _Error:
        return "ERR"
    except RecursionError:
        return "ERR"
    try:
        return _write(value)
    except _Error:
        return "ERR"
