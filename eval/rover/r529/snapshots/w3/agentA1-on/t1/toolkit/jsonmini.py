"""jsonmini 子命令: 迷你 JSON 规范化器。

导出: solve(text: str) -> str
  入参 text = 完整 stdin 文本; 返回 = 应写出的 stdout 文本 (末尾不带换行)。

支持 null / true / false / 十进制整数 / 字符串 / 数组 / 对象。
字符串内仅允许六种反斜杠转义 (双引号 / 反斜杠 / 斜杠 / n / t / uXXXX);
uXXXX 解码码点必须 >= 0x20。
对象重复键后者覆盖前者。
输出无任何空白; 字符串输出时把 双引号/反斜杠/换行/制表符 重新转义, 其余字符原样;
对象键按 Unicode 码点升序。
非法输入 (语法错误 / 结尾多余内容 / 非法转义 / 非法数字 / 空输入) 只输出一行 ERR。
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

    def peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ""

    def value(self):
        self.ws()
        c = self.peek()
        if c == "":
            raise _Err()
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c == '"':
            return self.string()
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
        if c == "n":
            if self.s.startswith("null", self.i):
                self.i += 4
                return ("null", None)
            raise _Err()
        if c == "-" or ("0" <= c <= "9"):
            return self.number()
        raise _Err()

    def number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "0":
            self.i += 1
            if self.i < self.n and "0" <= self.s[self.i] <= "9":
                raise _Err()
        elif "1" <= c <= "9":
            while self.i < self.n and "0" <= self.s[self.i] <= "9":
                self.i += 1
        else:
            raise _Err()
        tok = self.s[start:self.i]
        return ("int", int(tok))

    def string(self):
        self.i += 1  # 跳过开引号
        buf = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return ("str", "".join(buf))
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
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4:
                        raise _Err()
                    for ch in hexs:
                        if ch not in "0123456789abcdefABCDEF":
                            raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 5
                else:
                    raise _Err()
            elif ord(c) < 0x20:
                raise _Err()
            else:
                buf.append(c)
                self.i += 1

    def arr(self):
        self.i += 1  # 跳过 [
        items = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return ("arr", items)
        while True:
            items.append(self.value())
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return ("arr", items)
            raise _Err()

    def obj(self):
        self.i += 1  # 跳过 {
        pairs = {}
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return ("obj", pairs)
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Err()
            k = self.string()[1]
            self.ws()
            if self.peek() != ":":
                raise _Err()
            self.i += 1
            v = self.value()
            pairs[k] = v
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return ("obj", pairs)
            raise _Err()


def _escape_string(s):
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
    return '"' + "".join(out) + '"'


def _render(node):
    t, v = node
    if t == "null":
        return "null"
    if t == "bool":
        return "true" if v else "false"
    if t == "int":
        return str(v)
    if t == "str":
        return _escape_string(v)
    if t == "arr":
        return "[" + ",".join(_render(x) for x in v) + "]"
    if t == "obj":
        keys = sorted(v.keys())
        return "{" + ",".join(_escape_string(k) + ":" + _render(v[k]) for k in keys) + "}"
    raise _Err()


def solve(text: str):
    p = _Parser(text)
    try:
        node = p.value()
    except _Err:
        return "ERR"
    except Exception:
        return "ERR"
    p.ws()
    if p.i != p.n:
        return "ERR"
    try:
        return _render(node)
    except Exception:
        return "ERR"
