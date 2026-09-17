"""json_mini: parse a restricted JSON value and emit canonical compact text.

Rules:
- values: null/true/false/int/string/array/object
- ints: optional '-', no leading zeros, -0 => 0
- strings: escapes \\" \\\\ \\/ \\n \\t \\uXXXX only; decoded codepoint >= 0x20
- duplicate object keys: last wins; keys sorted by codepoint
- output: no whitespace; strings re-escape quote/backslash/newline/tab
- invalid input => "ERR"
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s: str):
        self.s = s
        self.i = 0
        self.n = len(s)

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in " \t\r\n":
            self.i += 1

    def parse_value(self):
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "n":
            self._lit("null")
            return None
        if c == "t":
            self._lit("true")
            return True
        if c == "f":
            self._lit("false")
            return False
        if c == '"':
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c.isdigit():
            return self.parse_int()
        raise _Err()

    def _lit(self, word: str):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def parse_int(self):
        start = self.i
        if self.i < self.n and self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        raw = self.s[start:self.i]
        # guard: body must be ascii digits
        body = raw[1:] if raw[0] == "-" else raw
        if not body.isdigit() or not body.isascii():
            raise _Err()
        val = int(raw)
        return val

    def parse_string(self):
        if self.s[self.i] != '"':
            raise _Err()
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
                e = self.s[self.i]
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
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4:
                        raise _Err()
                    for h in hexs:
                        if h not in "0123456789abcdefABCDEF":
                            raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err()
                self.i += 1
            else:
                if ord(c) < 0x20:
                    raise _Err()
                buf.append(c)
                self.i += 1

    def parse_array(self):
        self.i += 1
        arr = []
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return arr
        while True:
            self.skip_ws()
            arr.append(self.parse_value())
            self.skip_ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise _Err()

    def parse_object(self):
        self.i += 1
        obj = {}
        self.skip_ws()
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
            self.skip_ws()
            val = self.parse_value()
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


def _emit(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        out = ['"']
        for c in v:
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
    if isinstance(v, list):
        return "[" + ",".join(_emit(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(_emit(k) + ":" + _emit(v[k]) for k in keys) + "}"
    raise _Err()


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        p.skip_ws()
        if p.i >= p.n:
            return "ERR"
        v = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            return "ERR"
        return _emit(v)
    except _Err:
        return "ERR"
    except (ValueError, IndexError):
        return "ERR"
