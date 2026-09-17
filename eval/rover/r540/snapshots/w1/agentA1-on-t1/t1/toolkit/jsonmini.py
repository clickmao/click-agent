"""json_mini 子命令: 迷你 JSON 规范化器。

读入: STDIN 整体为一个 JSON 值 (可含前后空白与换行)。
支持 null / true / false / 十进制整数(可选负号; 不允许前导零, 允许 -0 => 输出为 0) /
      字符串 / 数组 / 对象(键为字符串)。
字符串内仅允许标准反斜杠转义 (\" \\ \/ \n \t \uXXXX 六种); uXXXX 解码为对应字符,
且解码出的码点必须 >= 0x20。
对象允许重复键, 重复时后者覆盖前者。
输出: 规范化文本, 不含任何空白; 字符串输出时把 引号/反斜杠/换行/制表符 重新转义,
      其余字符原样; 对象的键按 Unicode 码点升序。
非法输入 (语法错误 / 结尾有多余内容 / 非法转义 / 非法数字 / 空输入) => 只输出一行 ERR。
"""

_WS = " \t\n\r"


class _ParseError(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def _skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def parse(self):
        self._skip_ws()
        if self.i >= self.n:
            raise _ParseError()
        v = self._parse_value()
        self._skip_ws()
        if self.i != self.n:
            raise _ParseError()
        return v

    def _parse_value(self):
        if self.i >= self.n:
            raise _ParseError()
        c = self.s[self.i]
        if c == '"':
            return ("str", self._parse_string())
        if c == '{':
            return self._parse_object()
        if c == '[':
            return self._parse_array()
        if c == 'n':
            self._expect_lit("null")
            return ("null", None)
        if c == 't':
            self._expect_lit("true")
            return ("bool", True)
        if c == 'f':
            self._expect_lit("false")
            return ("bool", False)
        if c == '-' or c.isdigit():
            return ("int", self._parse_number())
        raise _ParseError()

    def _expect_lit(self, lit):
        if self.s[self.i:self.i + len(lit)] != lit:
            raise _ParseError()
        self.i += len(lit)

    def _parse_number(self):
        start = self.i
        if self.i < self.n and self.s[self.i] == '-':
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _ParseError()
        if self.s[self.i] == '0':
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _ParseError()  # 前导零
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        # 不允许小数点 / 指数 / 其他尾随字符 (由调用方 parse 校验结尾)
        tok = self.s[start:self.i]
        try:
            return int(tok)
        except ValueError:
            raise _ParseError()

    def _parse_string(self):
        if self.s[self.i] != '"':
            raise _ParseError()
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise _ParseError()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                break
            if c == '\\':
                self.i += 1
                if self.i >= self.n:
                    raise _ParseError()
                e = self.s[self.i]
                if e == '"':
                    buf.append('"')
                    self.i += 1
                elif e == '\\':
                    buf.append('\\')
                    self.i += 1
                elif e == '/':
                    buf.append('/')
                    self.i += 1
                elif e == 'n':
                    buf.append('\n')
                    self.i += 1
                elif e == 't':
                    buf.append('\t')
                    self.i += 1
                elif e == 'u':
                    self.i += 1
                    cp = self._parse_u4()
                    if cp < 0x20:
                        raise _ParseError()
                    buf.append(chr(cp))
                else:
                    raise _ParseError()
            else:
                # 原始字符: 控制字符 (含原始换行/制表) < 0x20 非法
                if ord(c) < 0x20:
                    raise _ParseError()
                buf.append(c)
                self.i += 1
        return "".join(buf)

    def _parse_u4(self):
        if self.i + 4 > self.n:
            raise _ParseError()
        h = self.s[self.i:self.i + 4]
        for ch in h:
            if ch not in "0123456789abcdefABCDEF":
                raise _ParseError()
        self.i += 4
        return int(h, 16)

    def _parse_array(self):
        self.i += 1  # '['
        items = []
        self._skip_ws()
        if self.i < self.n and self.s[self.i] == ']':
            self.i += 1
            return ("array", items)
        while True:
            self._skip_ws()
            items.append(self._parse_value())
            self._skip_ws()
            if self.i >= self.n:
                raise _ParseError()
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == ']':
                self.i += 1
                break
            raise _ParseError()
        return ("array", items)

    def _parse_object(self):
        self.i += 1  # '{'
        pairs = {}
        self._skip_ws()
        if self.i < self.n and self.s[self.i] == '}':
            self.i += 1
            return ("obj", pairs)
        while True:
            self._skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _ParseError()
            key = self._parse_string()
            self._skip_ws()
            if self.i >= self.n or self.s[self.i] != ':':
                raise _ParseError()
            self.i += 1
            self._skip_ws()
            val = self._parse_value()
            pairs[key] = val  # 重复键后者覆盖前者
            self._skip_ws()
            if self.i >= self.n:
                raise _ParseError()
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == '}':
                self.i += 1
                break
            raise _ParseError()
        return ("obj", pairs)


def _escape_string(s):
    parts = ['"']
    for c in s:
        if c == '"':
            parts.append('\\"')
        elif c == '\\':
            parts.append('\\\\')
        elif c == '\n':
            parts.append('\\n')
        elif c == '\t':
            parts.append('\\t')
        else:
            parts.append(c)
    parts.append('"')
    return "".join(parts)


def _emit(v):
    tag, data = v
    if tag == "null":
        return "null"
    if tag == "bool":
        return "true" if data else "false"
    if tag == "int":
        return str(data)
    if tag == "str":
        return _escape_string(data)
    if tag == "array":
        return "[" + ",".join(_emit(x) for x in data) + "]"
    if tag == "obj":
        keys = sorted(data.keys())
        return "{" + ",".join(_escape_string(k) + ":" + _emit(data[k]) for k in keys) + "}"
    raise _ParseError()


def solve(text: str) -> str:
    try:
        v = _Parser(text).parse()
    except _ParseError:
        return "ERR"
    try:
        return _emit(v)
    except _ParseError:
        return "ERR"
