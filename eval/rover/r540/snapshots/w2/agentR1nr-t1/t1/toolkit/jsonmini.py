"""json_mini: parse a mini-JSON value, emit canonical whitespace-free text."""


def _hexval(c):
    if "0" <= c <= "9":
        return ord(c) - 48
    if "a" <= c <= "f":
        return ord(c) - 87
    if "A" <= c <= "F":
        return ord(c) - 55
    return -1


class _Bad(Exception):
    pass


class _P:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n\r":
            self.i += 1

    def peek(self):
        if self.i < len(self.s):
            return self.s[self.i]
        return ""

    def value(self):
        c = self.peek()
        if c == "":
            raise _Bad()
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
        if c == "t":
            self.lit("true")
            return True
        if c == "f":
            self.lit("false")
            return False
        if c == "n":
            self.lit("null")
            return None
        if c == "-" or ("0" <= c <= "9"):
            return self.number()
        raise _Bad()

    def lit(self, w):
        if self.s[self.i:self.i + len(w)] != w:
            raise _Bad()
        self.i += len(w)

    def number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.peek() == "0":
            self.i += 1
            if "0" <= self.peek() <= "9":
                raise _Bad()
        elif "1" <= self.peek() <= "9":
            while "0" <= self.peek() <= "9":
                self.i += 1
        else:
            raise _Bad()
        return int(self.s[start:self.i])

    def string(self):
        if self.peek() != '"':
            raise _Bad()
        self.i += 1
        buf = []
        while True:
            if self.i >= len(self.s):
                raise _Bad()
            c = self.s[self.i]
            o = ord(c)
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= len(self.s):
                    raise _Bad()
                e = self.s[self.i]
                if e == '"':
                    buf.append('"')
                    self.i += 1
                elif e == "\\":
                    buf.append("\\")
                    self.i += 1
                elif e == "/":
                    buf.append("/")
                    self.i += 1
                elif e == "n":
                    buf.append("\n")
                    self.i += 1
                elif e == "t":
                    buf.append("\t")
                    self.i += 1
                elif e == "u":
                    cp = self.uni()
                    if 0xD800 <= cp <= 0xDBFF:
                        if self.s[self.i:self.i + 2] != "\\u":
                            raise _Bad()
                        self.i += 2
                        lo = self.uni()
                        if not (0xDC00 <= lo <= 0xDFFF):
                            raise _Bad()
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
                    elif 0xDC00 <= cp <= 0xDFFF:
                        raise _Bad()
                    if cp < 0x20:
                        raise _Bad()
                    buf.append(chr(cp))
                else:
                    raise _Bad()
            elif o < 0x20:
                raise _Bad()
            else:
                buf.append(c)
                self.i += 1

    def uni(self):
        if self.i >= len(self.s) or self.s[self.i] != "u":
            raise _Bad()
        self.i += 1
        h = self.s[self.i:self.i + 4]
        if len(h) != 4:
            raise _Bad()
        v = 0
        for ch in h:
            d = _hexval(ch)
            if d < 0:
                raise _Bad()
            v = v * 16 + d
        self.i += 4
        return v

    def arr(self):
        if self.peek() != "[":
            raise _Bad()
        self.i += 1
        res = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return res
        while True:
            res.append(self.value())
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.ws()
                continue
            if c == "]":
                self.i += 1
                return res
            raise _Bad()

    def obj(self):
        if self.peek() != "{":
            raise _Bad()
        self.i += 1
        d = {}
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return d
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Bad()
            key = self.string()
            self.ws()
            if self.peek() != ":":
                raise _Bad()
            self.i += 1
            self.ws()
            d[key] = self.value()
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return d
            raise _Bad()


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
        for ch in v:
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
    if isinstance(v, list):
        return "[" + ",".join(_emit(x) for x in v) + "]"
    if isinstance(v, dict):
        ks = sorted(v.keys())
        return "{" + ",".join(_emit(k) + ":" + _emit(v[k]) for k in ks) + "}"
    raise _Bad()


def solve(text: str) -> str:
    p = _P(text)
    try:
        p.ws()
        v = p.value()
        p.ws()
        if p.i != len(p.s):
            raise _Bad()
        return _emit(v)
    except _Bad:
        return "ERR"
    except Exception:
        return "ERR"
