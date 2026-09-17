"""json_mini subcommand: parse a JSON value and emit canonical compact text.

solve(text) -> str.
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\r\n":
            self.i += 1

    def parse_value(self):
        self.ws()
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == '"':
            return ("str", self.parse_string())
        if c == "n":
            if self.s.startswith("null", self.i):
                self.i += 4
                return ("null",)
            raise _Err()
        if c == "t":
            if self.s.startswith("true", self.i):
                self.i += 4
                return ("bool", True)
            raise _Err()
        if c == "f":
            if self.s.startswith("false", self.i):
                self.i += 5
                return ("bool", False)
            raise _Err()
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Err()

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        if self.i < self.n and self.s[self.i].isdigit():
            raise _Err()
        raw = self.s[start:self.i]
        try:
            v = int(raw)
        except Exception:
            raise _Err()
        return ("int", v, (raw != "-0"))

    def parse_string(self):
        # assumes current char is '"'
        assert self.s[self.i] == '"'
        self.i += 1
        chars = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                break
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
                e = self.s[self.i]
                if e == '"':
                    chars.append('"')
                    self.i += 1
                elif e == "\\":
                    chars.append("\\")
                    self.i += 1
                elif e == "/":
                    chars.append("/")
                    self.i += 1
                elif e == "n":
                    chars.append("\n")
                    self.i += 1
                elif e == "t":
                    chars.append("\t")
                    self.i += 1
                elif e == "u":
                    hx = self.s[self.i + 1:self.i + 5]
                    if len(hx) != 4:
                        raise _Err()
                    for ch in hx:
                        if ch not in "0123456789abcdefABCDEF":
                            raise _Err()
                    cp = int(hx, 16)
                    if cp < 0x20:
                        raise _Err()
                    chars.append(chr(cp))
                    self.i += 5
                else:
                    raise _Err()
            else:
                if ord(c) < 0x20:
                    raise _Err()
                chars.append(c)
                self.i += 1
        return "".join(chars)

    def parse_array(self):
        self.i += 1  # '['
        items = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return ("arr", items)
        while True:
            items.append(self.parse_value())
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                break
            raise _Err()
        return ("arr", items)

    def parse_object(self):
        self.i += 1  # '{'
        pairs = []  # list of (key, value)
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return ("obj", pairs)
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.parse_string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            val = self.parse_value()
            pairs.append((key, val))
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                break
            raise _Err()
        return ("obj", pairs)


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


def _canon(v):
    t = v[0]
    if t == "null":
        return "null"
    if t == "bool":
        return "true" if v[1] else "false"
    if t == "int":
        return str(v[1])
    if t == "str":
        return _esc(v[1])
    if t == "arr":
        return "[" + ",".join(_canon(x) for x in v[1]) + "]"
    if t == "obj":
        # later duplicate keys override earlier ones
        merged = {}
        for k, val in v[1]:
            merged[k] = val
        keys = sorted(merged.keys())
        return "{" + ",".join(_esc(k) + ":" + _canon(merged[k]) for k in keys) + "}"
    raise _Err()


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        p.ws()
        if p.i >= p.n:
            raise _Err()
        val = p.parse_value()
        p.ws()
        if p.i != p.n:
            raise _Err()
        return _canon(val)
    except _Err:
        return "ERR"
    except Exception:
        return "ERR"
