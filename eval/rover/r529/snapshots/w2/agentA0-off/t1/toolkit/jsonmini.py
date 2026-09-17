r"""json_mini: 迷你 JSON 解析 + 规范化输出.

solve(text) 接收该子命令的完整 stdin 文本, 返回应写出的 stdout 文本 (不带末尾换行).

规格:
  支持 null / true / false / 十进制整数 (可选负号; 不允许前导零, 允许 -0 => 输出 0) /
  字符串 / 数组 / 对象 (键为字符串).
  字符串内仅允许标准反斜杠转义 (\" \\ \/ \n \t \uXXXX 六种);
  \uXXXX 解码为对应字符, 且解码出的码点必须 >= 0x20.
  对象允许重复键, 后者覆盖前者.
  输出: 规范化文本, 不含任何空白;
    字符串输出时把 引号/反斜杠/换行/制表符 重新转义, 其余字符原样;
    对象的键按 Unicode 码点升序.
  输入非法 (语法错误 / 结尾有多余内容 / 非法转义 / 非法数字 / 空输入) => 只输出一行 ERR.
"""

WS = " \t\r\n"


class JErr(Exception):
    pass


class Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ""

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in WS:
            self.i += 1

    def parse_value(self):
        c = self.peek()
        if c == "":
            raise JErr("eof")
        if c == '"':
            return ("str", self.parse_string())
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "t":
            self.expect_word("true")
            return ("true", None)
        if c == "f":
            self.expect_word("false")
            return ("false", None)
        if c == "n":
            self.expect_word("null")
            return ("null", None)
        if c == "-" or ("0" <= c <= "9"):
            return ("num", self.parse_number())
        raise JErr("unexpected char")

    def expect_word(self, w):
        if self.s[self.i:self.i + len(w)] != w:
            raise JErr("bad literal")
        self.i += len(w)

    def parse_number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        # 整数部分
        if self.peek() == "0":
            self.i += 1
            if self.peek().isdigit():
                raise JErr("leading zero")
        elif "1" <= self.peek() <= "9":
            while self.peek().isdigit():
                self.i += 1
        else:
            raise JErr("bad number")
        # 不允许小数/指数部分 (规格只支持十进制整数)
        lit = self.s[start:self.i]
        try:
            return str(int(lit))
        except ValueError:
            raise JErr("bad number")

    def parse_string(self):
        # 假定当前是 '"'
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise JErr("unterminated string")
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise JErr("bad escape")
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
                        raise JErr("bad unicode escape")
                    hexs = self.s[self.i:self.i + 4]
                    if any(h not in "0123456789abcdefABCDEF" for h in hexs):
                        raise JErr("bad unicode hex")
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise JErr("cp < 0x20")
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    raise JErr("bad escape: " + e)
            elif ord(c) < 0x20:
                # 原始控制字符 (含原始换行/制表) 不允许直接出现
                raise JErr("raw control char")
            else:
                buf.append(c)
                self.i += 1

    def parse_array(self):
        self.i += 1  # '['
        self.skip_ws()
        items = []
        if self.peek() == "]":
            self.i += 1
            return ("arr", items)
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.skip_ws()
                continue
            if c == "]":
                self.i += 1
                return ("arr", items)
            raise JErr("bad array")

    def parse_object(self):
        self.i += 1  # '{'
        self.skip_ws()
        pairs = {}
        if self.peek() == "}":
            self.i += 1
            return ("obj", pairs)
        while True:
            if self.peek() != '"':
                raise JErr("bad key")
            key = self.parse_string()
            self.skip_ws()
            if self.peek() != ":":
                raise JErr("missing colon")
            self.i += 1
            self.skip_ws()
            val = self.parse_value()
            pairs[key] = val  # 后者覆盖前者
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.skip_ws()
                continue
            if c == "}":
                self.i += 1
                return ("obj", pairs)
            raise JErr("bad object")


def _escape_str(s):
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


def _dump(node):
    kind, val = node
    if kind == "null":
        return "null"
    if kind == "true":
        return "true"
    if kind == "false":
        return "false"
    if kind == "num":
        return val
    if kind == "str":
        return _escape_str(val)
    if kind == "arr":
        return "[" + ",".join(_dump(x) for x in val) + "]"
    if kind == "obj":
        keys = sorted(val.keys())
        return "{" + ",".join(_escape_str(k) + ":" + _dump(val[k]) for k in keys) + "}"
    raise JErr("bad node")


def solve(text):
    try:
        p = Parser(text)
        p.skip_ws()
        if p.i >= p.n:
            return "ERR"  # 空输入
        node = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            return "ERR"  # 多余内容
        return _dump(node)
    except JErr:
        return "ERR"
    except RecursionError:
        return "ERR"
