"""json_mini 子命令: 解析单个 JSON 值并输出无空白的规范化文本; 非法输入输出 ERR。"""

_WS = " \t\n\r"

_SIMPLE_ESCAPE = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "n": "\n",
    "t": "\t",
}

_OUT_ESCAPE = {
    '"': '\\"',
    "\\": "\\\\",
    "\n": "\\n",
    "\t": "\\t",
}


class _ParseError(Exception):
    pass


def _is_digit(ch):
    o = ord(ch)
    return 48 <= o <= 57


def _is_hex(ch):
    o = ord(ch)
    return (48 <= o <= 57) or (97 <= o <= 102) or (65 <= o <= 70)


def _hex_val(ch):
    o = ord(ch)
    if 48 <= o <= 57:
        return o - 48
    if 97 <= o <= 102:
        return o - 87
    return o - 55


def _int_str(value):
    """十进制整数转字符串。"""
    neg = value < 0
    if neg:
        value = -value
    digits = []
    while value > 0:
        digits.append(chr(48 + value % 10))
        value = value // 10
    if not digits:
        digits.append("0")
    if neg:
        digits.append("-")
    digits.reverse()
    return "".join(digits)


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def value(self):
        self.ws()
        if self.i >= self.n:
            raise _ParseError()
        ch = self.s[self.i]
        if ch == "{":
            return ("obj", self.obj())
        if ch == "[":
            return ("arr", self.arr())
        if ch == '"':
            return ("str", self.string())
        if ch == "t":
            self.word("true")
            return ("true", None)
        if ch == "f":
            self.word("false")
            return ("false", None)
        if ch == "n":
            self.word("null")
            return ("null", None)
        if ch == "-" or _is_digit(ch):
            return ("int", self.number())
        raise _ParseError()

    def word(self, word):
        end = self.i + len(word)
        if end > self.n or self.s[self.i:end] != word:
            raise _ParseError()
        self.i = end

    def number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n:
            raise _ParseError()
        ch = self.s[self.i]
        if ch == "0":
            self.i += 1
        elif "1" <= ch <= "9":
            while self.i < self.n and _is_digit(self.s[self.i]):
                self.i += 1
        else:
            raise _ParseError()
        if self.i < self.n and _is_digit(self.s[self.i]):
            raise _ParseError()
        val = 0
        for k in range(start, self.i):
            c = self.s[k]
            if _is_digit(c):
                val = val * 10 + (ord(c) - 48)
        if self.s[start] == "-":
            val = -val
        return val

    def string(self):
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise _ParseError()
            ch = self.s[self.i]
            if ch == '"':
                self.i += 1
                return "".join(buf)
            if ch == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _ParseError()
                esc = self.s[self.i]
                if esc == "u":
                    self.i += 1
                    cp = self.hex4()
                    if cp < 0x20 or 0xD800 <= cp <= 0xDFFF:
                        raise _ParseError()
                    buf.append(chr(cp))
                else:
                    rep = _SIMPLE_ESCAPE.get(esc)
                    if rep is None:
                        raise _ParseError()
                    buf.append(rep)
                    self.i += 1
            else:
                if ord(ch) < 0x20:
                    raise _ParseError()
                buf.append(ch)
                self.i += 1

    def hex4(self):
        if self.i + 4 > self.n:
            raise _ParseError()
        cp = 0
        for k in range(self.i, self.i + 4):
            c = self.s[k]
            if not _is_hex(c):
                raise _ParseError()
            cp = cp * 16 + _hex_val(c)
        self.i += 4
        return cp

    def arr(self):
        self.i += 1
        items = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.value())
            self.ws()
            if self.i >= self.n:
                raise _ParseError()
            ch = self.s[self.i]
            if ch == ",":
                self.i += 1
                continue
            if ch == "]":
                self.i += 1
                return items
            raise _ParseError()

    def obj(self):
        self.i += 1
        pairs = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return pairs
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _ParseError()
            key = self.string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _ParseError()
            self.i += 1
            pairs.append((key, self.value()))
            self.ws()
            if self.i >= self.n:
                raise _ParseError()
            ch = self.s[self.i]
            if ch == ",":
                self.i += 1
                continue
            if ch == "}":
                self.i += 1
                return pairs
            raise _ParseError()


def _merge(pairs):
    order = []
    data = {}
    for key, value in pairs:
        if key not in data:
            order.append(key)
        data[key] = value
    order.sort()
    return [(k, data[k]) for k in order]


def _string_out(text):
    buf = ['"']
    for ch in text:
        rep = _OUT_ESCAPE.get(ch)
        if rep is None:
            buf.append(ch)
        else:
            buf.append(rep)
    buf.append('"')
    return "".join(buf)


def _render(node):
    kind = node[0]
    if kind == "str":
        return _string_out(node[1])
    if kind == "int":
        return _int_str(node[1])
    if kind == "true":
        return "true"
    if kind == "false":
        return "false"
    if kind == "null":
        return "null"
    if kind == "arr":
        return "[" + ",".join(_render(v) for v in node[1]) + "]"
    body = []
    for key, value in _merge(node[1]):
        body.append(_string_out(key) + ":" + _render(value))
    return "{" + ",".join(body) + "}"


def solve(text: str) -> str:
    parser = _Parser(text)
    try:
        node = parser.value()
        parser.ws()
        if parser.i != parser.n:
            return "ERR"
        return _render(node)
    except _ParseError:
        return "ERR"
    except Exception:
        return "ERR"
