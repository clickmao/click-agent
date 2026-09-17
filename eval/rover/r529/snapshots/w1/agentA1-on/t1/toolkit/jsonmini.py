"""jsonmini 子命令: 迷你 JSON 规范化器。

solve(text) -> str: 入参为完整 stdin 文本, 返回规范化文本 (不含任何空白, 末尾不带换行)。
非法输入返回 "ERR"。

支持: null / true / false / 十进制整数(可选负号, 不允许前导零, -0 => 0) /
字符串 / 数组 / 对象(键为字符串)。字符串仅允许标准反斜杠转义 (\" \\ \\/ \\n \\t \\uXXXX),
uXXXX 解码码点必须 >= 0x20。对象重复键后者覆盖前者; 键按 Unicode 码点升序。
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def parse(self):
        self.ws()
        v = self.value()
        self.ws()
        if self.i != self.n:
            raise _Err()
        return v

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def value(self):
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return ("str", self.string())
        if c == "t":
            return self.lit("true", ("true",))
        if c == "f":
            return self.lit("false", ("false",))
        if c == "n":
            return self.lit("null", ("null",))
        if c == "-" or c.isdigit():
            return ("int", self.number())
        raise _Err()

    def lit(self, word, v):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return v
        raise _Err()

    def number(self):
        start = self.i
        if self.i < self.n and self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Err()  # 前导零
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        tok = self.s[start:self.i]
        # 禁止小数点/指数等
        if self.i < self.n and self.s[self.i] in ".eE":
            raise _Err()
        return int(tok)

    def string(self):
        # 前置: self.s[self.i] == '"'
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
                    self.i += 1
                    if self.i + 4 > self.n:
                        raise _Err()
                    h = self.s[self.i:self.i + 4]
                    if len(h) != 4:
                        raise _Err()
                    for ch in h:
                        if ch not in "0123456789abcdefABCDEF":
                            raise _Err()
                    cp = int(h, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err()  # 非法转义
            else:
                if ord(c) < 0x20:
                    raise _Err()  # 原始控制字符
                buf.append(c)
                self.i += 1

    def arr(self):
        self.i += 1  # '['
        items = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return ("arr", items)
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
                return ("arr", items)
            raise _Err()

    def obj(self):
        self.i += 1  # '{'
        pairs = {}
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return ("obj", pairs)
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
            pairs[key] = val  # 重复键后者覆盖前者
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return ("obj", pairs)
            raise _Err()


def _escape(s):
    buf = []
    for c in s:
        if c == '"':
            buf.append('\\"')
        elif c == "\\":
            buf.append("\\\\")
        elif c == "\n":
            buf.append("\\n")
        elif c == "\t":
            buf.append("\\t")
        else:
            buf.append(c)
    return "".join(buf)


def _emit(v):
    t = v[0]
    if t == "null":
        return "null"
    if t == "true":
        return "true"
    if t == "false":
        return "false"
    if t == "int":
        return str(v[1])
    if t == "str":
        return '"' + _escape(v[1]) + '"'
    if t == "arr":
        return "[" + ",".join(_emit(x) for x in v[1]) + "]"
    if t == "obj":
        keys = sorted(v[1].keys())
        return "{" + ",".join('"' + _escape(k) + '":' + _emit(v[1][k]) for k in keys) + "}"
    raise _Err()


def solve(text):
    if text.strip() == "":
        return "ERR"
    try:
        p = _Parser(text)
        v = p.parse()
        return _emit(v)
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
