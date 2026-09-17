"""jsonmini 子命令: 极简 JSON 解析与规范化输出。

solve(text) -> str
  text: 完整 stdin 文本, 整体为一个 JSON 值 (可含前后空白)。
  返回: 不含任何空白的规范化文本 (末尾不带换行); 非法输入返回 "ERR"。

支持: null / true / false / 十进制整数(可选负号, 无前导零, -0 -> 0) /
      字符串 / 数组 / 对象(键为字符串)。
字符串: 仅允许 \\" \\\\ \\/ \\n \\t \\uXXXX 六种转义; 解码出的码点 >= 0x20。
对象: 重复键后者覆盖; 输出时键按 Unicode 码点升序。
输出转义: 引号/反斜杠/换行/制表符重新转义, 其余字符原样。
"""
import sys

ERR = "ERR"
_WS = " \t\n\r"


class ParseError(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def skip_ws(self):
        s, n = self.s, len(self.s)
        while self.i < n and s[self.i] in _WS:
            self.i += 1

    def parse_value(self):
        if self.i >= len(self.s):
            raise ParseError()
        c = self.s[self.i]
        if c == '"':
            return self.parse_string()
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == "t":
            return self.literal("true", True)
        if c == "f":
            return self.literal("false", False)
        if c == "n":
            return self.literal("null", None)
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise ParseError()

    def literal(self, word, value):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return value
        raise ParseError()

    def parse_number(self):
        s, n = self.s, len(self.s)
        start = self.i
        if self.i < n and s[self.i] == "-":
            self.i += 1
        if self.i >= n or not s[self.i].isdigit():
            raise ParseError()
        if s[self.i] == "0":
            self.i += 1
            if self.i < n and s[self.i].isdigit():
                raise ParseError()  # 前导零
        else:
            while self.i < n and s[self.i].isdigit():
                self.i += 1
        return int(s[start:self.i])

    def parse_string(self):
        s, n = self.s, len(self.s)
        self.i += 1  # 开引号
        buf = []
        while True:
            if self.i >= n:
                raise ParseError()
            c = s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= n:
                    raise ParseError()
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
                        raise ParseError()
                    hx = s[self.i + 1:self.i + 5]
                    if len(hx) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hx):
                        raise ParseError()
                    cp = int(hx, 16)
                    if cp < 0x20:
                        raise ParseError()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    raise ParseError()
                self.i += 1
            else:
                if ord(c) < 0x20:
                    raise ParseError()  # 原始控制字符
                buf.append(c)
                self.i += 1

    def parse_array(self):
        self.i += 1  # [
        arr = []
        self.skip_ws()
        if self.i < len(self.s) and self.s[self.i] == "]":
            self.i += 1
            return arr
        while True:
            self.skip_ws()
            arr.append(self.parse_value())
            self.skip_ws()
            if self.i >= len(self.s):
                raise ParseError()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise ParseError()

    def parse_object(self):
        self.i += 1  # {
        pairs = {}
        self.skip_ws()
        if self.i < len(self.s) and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.skip_ws()
            if self.i >= len(self.s) or self.s[self.i] != '"':
                raise ParseError()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= len(self.s) or self.s[self.i] != ":":
                raise ParseError()
            self.i += 1
            self.skip_ws()
            val = self.parse_value()
            pairs[key] = val
            self.skip_ws()
            if self.i >= len(self.s):
                raise ParseError()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return pairs
            raise ParseError()


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


def _norm(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"' + _escape(v) + '"'
    if isinstance(v, list):
        return "[" + ",".join(_norm(x) for x in v) + "]"
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda kv: kv[0])
        return "{" + ",".join(
            '"' + _escape(k) + '":' + _norm(val) for k, val in items
        ) + "}"
    return ERR


def solve(text):
    p = _Parser(text)
    try:
        p.skip_ws()
        v = p.parse_value()
        p.skip_ws()
        if p.i != len(p.s):
            return ERR  # 结尾多余内容
    except ParseError:
        return ERR
    except (ValueError, IndexError):
        return ERR
    return _norm(v)


if __name__ == "__main__":
    sys.stdout.write(solve(sys.stdin.read()))
