"""json_mini: 极简 JSON 规范化器。solve(text) -> str (stdout 文本, 末尾不带换行)。"""

ERR = "ERR"


class _Fail(Exception):
    pass


_WS = " \t\n\r"


class Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ""

    def parse(self):
        self.ws()
        v = self.value()
        self.ws()
        if self.i != self.n:
            raise _Fail()
        return v

    def value(self):
        c = self.peek()
        if c == "":
            raise _Fail()
        if c == "n":
            if self.s.startswith("null", self.i):
                self.i += 4
                return ("null",)
            raise _Fail()
        if c == "t":
            if self.s.startswith("true", self.i):
                self.i += 4
                return ("bool", True)
            raise _Fail()
        if c == "f":
            if self.s.startswith("false", self.i):
                self.i += 5
                return ("bool", False)
            raise _Fail()
        if c == '"':
            return ("str", self.string())
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        if c == "-" or c.isdigit():
            return ("num", self.number())
        raise _Fail()

    def number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Fail()
        if self.s[self.i] == "0":
            self.i += 1
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        # 结尾不允许紧跟更多数字类字符 (无小数点/指数)
        if self.i < self.n and (self.s[self.i].isdigit()):
            raise _Fail()
        return int(self.s[start:self.i])

    def string(self):
        # 前置: s[i] == '"'
        self.i += 1
        out = []
        while True:
            if self.i >= self.n:
                raise _Fail()
            c = self.s[self.i]
            self.i += 1
            if c == '"':
                return "".join(out)
            if c == "\\":
                if self.i >= self.n:
                    raise _Fail()
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
                        raise _Fail()
                    hx = self.s[self.i:self.i + 4]
                    for ch in hx:
                        if ch not in "0123456789abcdefABCDEF":
                            raise _Fail()
                    cp = int(hx, 16)
                    self.i += 4
                    if cp < 0x20:
                        raise _Fail()
                    out.append(chr(cp))
                else:
                    raise _Fail()
            else:
                if ord(c) < 0x20:
                    raise _Fail()
                out.append(c)

    def array(self):
        # 前置: s[i] == '['
        self.i += 1
        items = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return ("arr", items)
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
                return ("arr", items)
            raise _Fail()

    def obj(self):
        # 前置: s[i] == '{'
        self.i += 1
        pairs = {}
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return ("obj", pairs)
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Fail()
            key = self.string()
            self.ws()
            if self.peek() != ":":
                raise _Fail()
            self.i += 1
            self.ws()
            val = self.value()
            pairs[key] = val
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return ("obj", pairs)
            raise _Fail()


def _render(v):
    tag = v[0]
    if tag == "null":
        return "null"
    if tag == "bool":
        return "true" if v[1] else "false"
    if tag == "num":
        return str(v[1])
    if tag == "str":
        return _render_str(v[1])
    if tag == "arr":
        return "[" + ",".join(_render(x) for x in v[1]) + "]"
    # obj
    pairs = v[1]
    keys = sorted(pairs.keys())
    return "{" + ",".join(_render_str(k) + ":" + _render(pairs[k]) for k in keys) + "}"


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
        v = Parser(text).parse()
    except _Fail:
        return ERR
    except RecursionError:
        return ERR
    return _render(v)
