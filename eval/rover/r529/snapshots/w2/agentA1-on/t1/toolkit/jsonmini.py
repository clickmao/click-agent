"""json_mini 子命令: 极简 JSON 解析 + 规范化输出。

solve(text) 接收完整 stdin 文本, 返回规范化文本 (不含任何空白)。
非法输入返回 "ERR"。
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def parse_value(self):
        self.skip_ws()
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == "n":
            self._lit("null")
            return None
        if c == "t":
            self._lit("true")
            return True
        if c == "f":
            self._lit("false")
            return False
        if c == '"':
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Err()

    def _lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def parse_number(self):
        start = self.i
        if self.i < self.n and self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Err()
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        return int(self.s[start:self.i])

    def parse_string(self):
        if self.s[self.i] != '"':
            raise _Err()
        self.i += 1
        chars = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
                e = self.s[self.i]
                if e == '"':
                    chars.append('"')
                elif e == "\\":
                    chars.append("\\")
                elif e == "/":
                    chars.append("/")
                elif e == "n":
                    chars.append("\n")
                elif e == "t":
                    chars.append("\t")
                elif e == "u":
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(
                        ch not in "0123456789abcdefABCDEF" for ch in hexs
                    ):
                        raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    chars.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err()
                self.i += 1
            else:
                if ord(c) < 0x20:
                    raise _Err()
                chars.append(c)
                self.i += 1

    def parse_array(self):
        self.i += 1  # [
        items = []
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.parse_value())
            self.skip_ws()
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

    def parse_object(self):
        self.i += 1  # {
        pairs = {}
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            val = self.parse_value()
            pairs[key] = val
            self.skip_ws()
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


def _encode_string(s):
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


def _encode(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _encode_string(v)
    if isinstance(v, list):
        return "[" + ",".join(_encode(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(_encode_string(k) + ":" + _encode(v[k]) for k in keys) + "}"
    return "ERR"


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        val = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            return "ERR"
        return _encode(val)
    except _Err:
        return "ERR"
    except Exception:
        return "ERR"
