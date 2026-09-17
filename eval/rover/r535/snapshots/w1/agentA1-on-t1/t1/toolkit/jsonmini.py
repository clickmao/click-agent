"""json_mini: 极简 JSON 解析 + 规范化输出。

solve(text) -> str
  支持: null / true / false / 十进制整数(可负; 无前导零; -0 => 0) /
        字符串 / 数组 / 对象(键为字符串)。
  字符串转义: \\" \\\\ \\/ \\n \\t \\uXXXX (码点 >= 0x20)。
  对象重复键后者覆盖前者; 输出无任何空白; 键按 Unicode 码点升序。
  非法输入 -> "ERR"。

内部节点类型标记:
  ("null", None) / ("b", bool) / ("i", int) / ("s", str) / ("a", list) / ("o", dict)
"""


class _Err(Exception):
    pass


class _Parser:
    __slots__ = ("s", "i", "n")

    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def ws(self):
        s = self.s
        i = self.i
        n = self.n
        while i < n and s[i] in " \t\n\r":
            i += 1
        self.i = i

    def value(self):
        self.ws()
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == '"':
            return ("s", self.string())
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        if c == "t":
            self.lit("true")
            return ("b", True)
        if c == "f":
            self.lit("false")
            return ("b", False)
        if c == "n":
            self.lit("null")
            return ("null", None)
        if c == "-" or c.isdigit():
            return self.number()
        raise _Err()

    def lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def number(self):
        s = self.s
        start = self.i
        if s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not s[self.i].isdigit():
            raise _Err()
        if s[self.i] == "0":
            self.i += 1
            if self.i < self.n and s[self.i].isdigit():
                raise _Err()
        else:
            while self.i < self.n and s[self.i].isdigit():
                self.i += 1
        return ("i", int(s[start:self.i]))

    def string(self):
        s = self.s
        n = self.n
        if s[self.i] != '"':
            raise _Err()
        self.i += 1
        buf = []
        while True:
            if self.i >= n:
                raise _Err()
            c = s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= n:
                    raise _Err()
                e = s[self.i]
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
                    if self.i + 4 >= n:
                        raise _Err()
                    hexs = s[self.i + 1:self.i + 5]
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

    def array(self):
        self.i += 1
        items = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return ("a", items)
        while True:
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
                return ("a", items)
            raise _Err()

    def obj(self):
        self.i += 1
        pairs = {}
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return ("o", pairs)
        while True:
            self.ws()
            key = self.string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
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
                return ("o", pairs)
            raise _Err()


def _escape(s):
    out = []
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
    return "".join(out)


def _render(node):
    t = node[0]
    if t == "null":
        return "null"
    if t == "b":
        return "true" if node[1] else "false"
    if t == "i":
        return str(node[1])
    if t == "s":
        return '"' + _escape(node[1]) + '"'
    if t == "a":
        return "[" + ",".join(_render(x) for x in node[1]) + "]"
    pairs = node[1]
    keys = sorted(pairs.keys())
    return "{" + ",".join(
        '"' + _escape(k) + '":' + _render(pairs[k]) for k in keys
    ) + "}"


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        v = p.value()
        p.ws()
        if p.i != p.n:
            return "ERR"
    except _Err:
        return "ERR"
    except (IndexError, ValueError, RecursionError):
        return "ERR"
    return _render(v)
