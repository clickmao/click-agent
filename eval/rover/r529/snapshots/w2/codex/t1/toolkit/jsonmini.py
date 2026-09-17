class _Err(Exception):
    pass


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        value = p.parse_value()
        p.skip_ws()
        if p.pos != len(p.text):
            raise _Err()
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
    return _render(value)


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.n = len(text)

    def skip_ws(self) -> None:
        t = self.text
        n = self.n
        i = self.pos
        while i < n and t[i] in " \t\n\r":
            i += 1
        self.pos = i

    def parse_value(self):
        self.skip_ws()
        if self.pos >= self.n:
            raise _Err()
        c = self.text[self.pos]
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == '"':
            return ("str", self.parse_string())
        if c == "t":
            self.expect_lit("true")
            return ("bool", True)
        if c == "f":
            self.expect_lit("false")
            return ("bool", False)
        if c == "n":
            self.expect_lit("null")
            return ("null", None)
        if c == "-" or c.isdigit():
            return ("int", self.parse_number())
        raise _Err()

    def expect_lit(self, lit: str) -> None:
        if self.text.startswith(lit, self.pos):
            self.pos += len(lit)
        else:
            raise _Err()

    def parse_object(self):
        self.pos += 1
        result = {}
        self.skip_ws()
        if self.pos < self.n and self.text[self.pos] == "}":
            self.pos += 1
            return ("obj", result)
        while True:
            self.skip_ws()
            if self.pos >= self.n or self.text[self.pos] != '"':
                raise _Err()
            key = self.parse_string()
            self.skip_ws()
            if self.pos >= self.n or self.text[self.pos] != ":":
                raise _Err()
            self.pos += 1
            value = self.parse_value()
            result[key] = value
            self.skip_ws()
            if self.pos >= self.n:
                raise _Err()
            c = self.text[self.pos]
            if c == ",":
                self.pos += 1
                continue
            if c == "}":
                self.pos += 1
                return ("obj", result)
            raise _Err()

    def parse_array(self):
        self.pos += 1
        items = []
        self.skip_ws()
        if self.pos < self.n and self.text[self.pos] == "]":
            self.pos += 1
            return ("arr", items)
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            if self.pos >= self.n:
                raise _Err()
            c = self.text[self.pos]
            if c == ",":
                self.pos += 1
                continue
            if c == "]":
                self.pos += 1
                return ("arr", items)
            raise _Err()

    def parse_string(self) -> str:
        i = self.pos + 1
        text = self.text
        n = self.n
        out = []
        while i < n:
            c = text[i]
            if c == '"':
                self.pos = i + 1
                return "".join(out)
            if c == "\\":
                i += 1
                if i >= n:
                    raise _Err()
                e = text[i]
                if e == '"':
                    out.append('"')
                elif e == "\\":
                    out.append("\\")
                elif e == "/":
                    out.append("/")
                elif e == "n":
                    out.append("\n")
                elif e == "t":
                    out.append("\t")
                elif e == "u":
                    code = self.parse_u(i)
                    out.append(chr(code))
                    i += 4
                else:
                    raise _Err()
                i += 1
                continue
            if c < " ":
                raise _Err()
            out.append(c)
            i += 1
        raise _Err()

    def parse_u(self, i: int) -> int:
        hexs = self.text[i + 1:i + 5]
        if len(hexs) != 4:
            raise _Err()
        for ch in hexs:
            if ch not in "0123456789abcdefABCDEF":
                raise _Err()
        code = int(hexs, 16)
        if code < 0x20:
            raise _Err()
        return code

    def parse_number(self) -> int:
        text = self.text
        n = self.n
        i = self.pos
        neg = False
        if text[i] == "-":
            neg = True
            i += 1
            if i >= n:
                raise _Err()
        if not text[i].isdigit():
            raise _Err()
        if text[i] == "0":
            if i + 1 < n and text[i + 1].isdigit():
                raise _Err()
            i += 1
        else:
            while i < n and text[i].isdigit():
                i += 1
        value = int(text[self.pos:i])
        self.pos = i
        return value


def _render(value) -> str:
    kind, data = value
    if kind == "null":
        return "null"
    if kind == "bool":
        return "true" if data else "false"
    if kind == "int":
        return str(data)
    if kind == "str":
        return _render_string(data)
    if kind == "arr":
        return "[" + ",".join(_render(v) for v in data) + "]"
    parts = []
    for key in sorted(data.keys()):
        parts.append(_render_string(key) + ":" + _render(data[key]))
    return "{" + ",".join(parts) + "}"


def _render_string(s: str) -> str:
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
