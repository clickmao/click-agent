"""Multi-file toolkit: `jsonmini` subcommand.

`solve` reads the whole stdin text for the `json_mini` family and returns the
canonical stdout text (no trailing newline, no whitespace).
"""


class _JErr(Exception):
    pass


_WS = " \t\n\r"
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t"}
_HEXC = "0123456789abcdefABCDEF"


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        s = self.s
        n = len(s)
        while self.i < n and s[self.i] in _WS:
            self.i += 1

    def eof(self):
        return self.i >= len(self.s)

    def parse(self):
        self.ws()
        if self.eof():
            raise _JErr()
        value = self.value()
        self.ws()
        if not self.eof():
            raise _JErr()
        return value

    def value(self):
        s = self.s
        i = self.i
        if i >= len(s):
            raise _JErr()
        c = s[i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
        if s.startswith("null", i):
            self.i = i + 4
            return None
        if s.startswith("true", i):
            self.i = i + 4
            return True
        if s.startswith("false", i):
            self.i = i + 5
            return False
        if c == "-" or c.isdigit():
            return self.number()
        raise _JErr()

    def number(self):
        s = self.s
        n = len(s)
        i = self.i
        start = i
        if s[i] == "-":
            i += 1
            if i >= n or not s[i].isdigit():
                raise _JErr()
        if s[i] == "0":
            i += 1
        else:
            if not ("1" <= s[i] <= "9"):
                raise _JErr()
            while i < n and s[i].isdigit():
                i += 1
        self.i = i
        return int(s[start:i])

    def string(self):
        s = self.s
        n = len(s)
        i = self.i
        if s[i] != '"':
            raise _JErr()
        i += 1
        out = []
        while True:
            if i >= n:
                raise _JErr()
            c = s[i]
            if c == '"':
                self.i = i + 1
                return "".join(out)
            if c == "\\":
                i += 1
                if i >= n:
                    raise _JErr()
                e = s[i]
                if e in _ESCAPES:
                    out.append(_ESCAPES[e])
                    i += 1
                elif e == "u":
                    if i + 4 >= n:
                        raise _JErr()
                    hexs = s[i + 1:i + 5]
                    for h in hexs:
                        if h not in _HEXC:
                            raise _JErr()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _JErr()
                    out.append(chr(cp))
                    i += 5
                else:
                    raise _JErr()
            else:
                if ord(c) < 0x20:
                    raise _JErr()
                out.append(c)
                i += 1

    def arr(self):
        s = self.s
        self.i += 1
        result = []
        self.ws()
        if self.i < len(s) and s[self.i] == "]":
            self.i += 1
            return result
        while True:
            self.ws()
            result.append(self.value())
            self.ws()
            if self.i >= len(s):
                raise _JErr()
            c = s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return result
            raise _JErr()

    def obj(self):
        s = self.s
        self.i += 1
        items = []
        self.ws()
        if self.i < len(s) and s[self.i] == "}":
            self.i += 1
            return items
        while True:
            self.ws()
            if self.i >= len(s) or s[self.i] != '"':
                raise _JErr()
            key = self.string()
            self.ws()
            if self.i >= len(s) or s[self.i] != ":":
                raise _JErr()
            self.i += 1
            self.ws()
            val = self.value()
            items.append((key, val))
            self.ws()
            if self.i >= len(s):
                raise _JErr()
            c = s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return items
            raise _JErr()


def _encode_string(s):
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


def _encode(value):
    out = []
    _emit(value, out)
    return "".join(out)


def _emit(value, out):
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, str):
        out.append(_encode_string(value))
    elif isinstance(value, list):
        out.append("[")
        for idx, item in enumerate(value):
            if idx:
                out.append(",")
            _emit(item, out)
        out.append("]")
    else:
        merged = {}
        for key, val in value:
            merged[key] = val
        out.append("{")
        first = True
        for key in sorted(merged):
            if not first:
                out.append(",")
            first = False
            out.append(_encode_string(key))
            out.append(":")
            _emit(merged[key], out)
        out.append("}")
    return out


def solve(text: str) -> str:
    try:
        value = _Parser(text).parse()
        return _encode(value)
    except _JErr:
        return "ERR"
    except RecursionError:
        return "ERR"
