"""json_mini 子命令: 极简 JSON 解析 + 规范化输出.

solve(text) -> str : 入参为该子命令完整 stdin 文本, 返回应当写出的 stdout 文本(末尾不带换行).
"""

_ERR = "ERR"
_WS = " \t\n\r"

_SIMPLE_ESC = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t"}


class _Bad(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in _WS:
            self.i += 1

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def parse_value(self):
        c = self.peek()
        if c == "":
            raise _Bad("eof")
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
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Bad("value")

    def lit(self, word):
        if self.s.startswith(word, self.i):
            self.i += len(word)
        else:
            raise _Bad("literal")

    def parse_string(self):
        if self.peek() != '"':
            raise _Bad("string")
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.s):
                raise _Bad("eof str")
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                if self.i >= len(self.s):
                    raise _Bad("eof esc")
                e = self.s[self.i]
                if e in _SIMPLE_ESC:
                    out.append(_SIMPLE_ESC[e])
                    self.i += 1
                elif e == "u":
                    if self.i + 4 >= len(self.s):
                        raise _Bad("u short")
                    hexs = self.s[self.i + 1:self.i + 5]
                    try:
                        cp = int(hexs, 16)
                    except Exception:
                        raise _Bad("u hex")
                    if len(hexs) != 4:
                        raise _Bad("u hex")
                    if cp < 0x20:
                        raise _Bad("u ctrl")
                    out.append(chr(cp))
                    self.i += 5
                else:
                    raise _Bad("esc")
            elif ord(c) < 0x20:
                raise _Bad("raw ctrl")
            else:
                out.append(c)
                self.i += 1

    def parse_number(self):
        start = self.i
        if self.peek() == "-":
            self.i += 1
        if self.i >= len(self.s):
            raise _Bad("num")
        c = self.s[self.i]
        if c == "0":
            self.i += 1
            if self.i < len(self.s) and self.s[self.i].isdigit():
                raise _Bad("lead zero")
        elif c.isdigit():
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
        else:
            raise _Bad("num")
        return int(self.s[start:self.i])

    def parse_array(self):
        self.i += 1  # [
        arr = []
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return arr
        while True:
            self.ws()
            arr.append(self.parse_value())
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise _Bad("array")

    def parse_object(self):
        self.i += 1  # {
        obj = {}
        order = []
        self.ws()
        if self.peek() == "}":
            self.i += 1
            return obj
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Bad("key")
            key = self.parse_string()
            self.ws()
            if self.peek() != ":":
                raise _Bad("colon")
            self.i += 1
            self.ws()
            val = self.parse_value()
            if key not in obj:
                order.append(key)
            obj[key] = val
            self.ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _Bad("object")


def _enc_string(s):
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


def _dump(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _enc_string(v)
    if isinstance(v, list):
        return "[" + ",".join(_dump(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys(), key=lambda k: [ord(c) for c in k])
        return "{" + ",".join(_enc_string(k) + ":" + _dump(v[k]) for k in keys) + "}"
    raise _Bad("dump")


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        p.ws()
        if p.i >= len(p.s):
            return _ERR
        val = p.parse_value()
        p.ws()
        if p.i != len(p.s):
            return _ERR
        return _dump(val)
    except _Bad:
        return _ERR
    except RecursionError:
        return _ERR
