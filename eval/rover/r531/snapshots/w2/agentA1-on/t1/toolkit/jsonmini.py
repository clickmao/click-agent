"""jsonmini 子命令: 极简 JSON 解析 + 规范化输出.

solve(text) -> str: 入参为完整 stdin 文本, 返回规范化文本(不含任何空白), 非法则 "ERR".
"""

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t"}


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

    def parse(self):
        self.ws()
        v = self.value()
        self.ws()
        if self.i != self.n:
            raise _Err()
        return v

    def value(self):
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "n":
            self.lit("null")
            return None
        if c == "t":
            self.lit("true")
            return True
        if c == "f":
            self.lit("false")
            return False
        if c == '"':
            return self.string()
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        if c == "-" or c.isdigit():
            return self.number()
        raise _Err()

    def lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n:
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Err()
        elif self.s[self.i].isdigit():
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        else:
            raise _Err()
        # 小数/指数均不允许
        if self.i < self.n and self.s[self.i] in ".eE":
            raise _Err()
        return int(self.s[start:self.i])

    def string(self):
        # 调用时 self.s[self.i] == '"'
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
                if e == "u":
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(h not in "0123456789abcdefABCDEF" for h in hexs):
                        raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 5
                elif e in _ESCAPES:
                    buf.append(_ESCAPES[e])
                    self.i += 1
                else:
                    raise _Err()
            elif ord(c) < 0x20:
                raise _Err()
            else:
                buf.append(c)
                self.i += 1

    def array(self):
        self.i += 1  # '['
        self.ws()
        items = []
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            self.ws()
            items.append(self.value())
            self.ws()
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

    def obj(self):
        self.i += 1  # '{'
        self.ws()
        pairs = {}
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            self.ws()
            val = self.value()
            pairs[key] = val
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return pairs
            raise _Err()


def _dump(v) -> str:
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
        return "[" + ",".join(_dump(x) for x in v) + "]"
    # dict
    keys = sorted(v.keys(), key=lambda k: [ord(c) for c in k])
    return "{" + ",".join(_dump(k) + ":" + _dump(v[k]) for k in keys) + "}"


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        val = p.parse()
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
    return _dump(val)
