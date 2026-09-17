"""json_mini 子命令: 一个极简 JSON 解析 + 规范化输出器。

规格:
  输入: 整体为一个 JSON 值 (可含前后空白与换行)。
  支持: null / true / false / 十进制整数(可选负号, 不允许前导零, 允许 -0 => 输出 0)
        / 字符串 / 数组 / 对象(键为字符串)。
  字符串仅允许标准反斜杠转义 (\\" \\\\ \\/ \\n \\t \\uXXXX 六种);
        uXXXX 解码为对应字符, 且解码出的码点必须 >= 0x20。
  对象允许重复键, 重复时后者覆盖前者。
  输出: 规范化文本, 不含任何空白:
        字符串输出时把 引号/反斜杠/换行/制表符 重新转义, 其余字符原样;
        对象的键按 Unicode 码点升序。
  非法 (语法错误 / 结尾多余内容 / 非法转义 / 非法数字 / 空输入) => 只输出 "ERR"。
"""


class _Bad(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def _err(self):
        raise _Bad()

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\r\n":
            self.i += 1

    def parse_value(self):
        self.ws()
        if self.i >= self.n:
            self._err()
        c = self.s[self.i]
        if c == "n":
            self._lit("null")
            return ("null", None)
        if c == "t":
            self._lit("true")
            return ("bool", True)
        if c == "f":
            self._lit("false")
            return ("bool", False)
        if c == '"':
            return ("str", self.parse_string())
        if c == "[":
            return ("arr", self.parse_array())
        if c == "{":
            return ("obj", self.parse_object())
        if c == "-" or c.isdigit():
            return ("int", self.parse_int())
        self._err()

    def _lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            self._err()
        self.i += len(word)

    def parse_string(self):
        if self.s[self.i] != '"':
            self._err()
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                self._err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    self._err()
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
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        self._err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        self._err()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    self._err()
                self.i += 1
            else:
                if ord(c) < 0x20:
                    self._err()
                buf.append(c)
                self.i += 1

    def parse_int(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.i >= self.n or not self.s[self.i].isdigit():
                self._err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                self._err()  # 前导零
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        tok = self.s[start:self.i]
        try:
            return int(tok)
        except ValueError:
            self._err()

    def parse_array(self):
        self.i += 1  # [
        items = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.parse_value())
            self.ws()
            if self.i >= self.n:
                self._err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            self._err()

    def parse_object(self):
        self.i += 1  # {
        pairs = {}
        order = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                self._err()
            key = self.parse_string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                self._err()
            self.i += 1
            val = self.parse_value()
            if key not in pairs:
                order.append(key)
            pairs[key] = val
            self.ws()
            if self.i >= self.n:
                self._err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return pairs
            self._err()


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
    return '"' + "".join(out) + '"'


def _render(v):
    tag, val = v
    if tag == "null":
        return "null"
    if tag == "bool":
        return "true" if val else "false"
    if tag == "int":
        return str(val)
    if tag == "str":
        return _escape(val)
    if tag == "arr":
        return "[" + ",".join(_render(x) for x in val) + "]"
    if tag == "obj":
        keys = sorted(val.keys())
        return "{" + ",".join(_escape(k) + ":" + _render(val[k]) for k in keys) + "}"
    raise _Bad()


def solve(text):
    """纯函数: 输入完整 stdin 文本, 返回应写出的 stdout 文本 (末尾不含换行)。"""
    if text.strip() == "":
        return "ERR"
    p = _Parser(text)
    try:
        v = p.parse_value()
        p.ws()
        if p.i != p.n:
            return "ERR"
        return _render(v)
    except _Bad:
        return "ERR"
    except RecursionError:
        return "ERR"
