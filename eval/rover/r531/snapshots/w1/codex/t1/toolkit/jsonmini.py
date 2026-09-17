"""Mini JSON parser/normalizer subcommand."""


class _Bad(Exception):
    pass


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def parse_value(self):
        if self.i >= self.n:
            raise _Bad()
        c = self.s[self.i]
        if c == '"':
            return self.parse_string()
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == "t" and self.s.startswith("true", self.i):
            self.i += 4
            return True
        if c == "f" and self.s.startswith("false", self.i):
            self.i += 5
            return False
        if c == "n" and self.s.startswith("null", self.i):
            self.i += 4
            return None
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Bad()

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
        if self.i >= self.n or not self.s[self.i].isdigit():
            raise _Bad()
        if self.s[self.i] == "0":
            self.i += 1
            if self.i < self.n and self.s[self.i].isdigit():
                raise _Bad()
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        # any following digit counts as part of the number token
        if self.i < self.n and (self.s[self.i].isdigit() or self.s[self.i] == "."):
            raise _Bad()
        return int(self.s[start:self.i])

    def parse_string(self):
        self.i += 1  # opening quote
        out = []
        while True:
            if self.i >= self.n:
                raise _Bad()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(out)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Bad()
                e = self.s[self.i]
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
                    if self.i + 4 >= self.n:
                        raise _Bad()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        raise _Bad()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Bad()
                    out.append(chr(cp))
                    self.i += 4
                else:
                    raise _Bad()
                self.i += 1
            else:
                if c == '"':
                    raise _Bad()
                if c in "\n\r\t":
                    raise _Bad()
                out.append(c)
                self.i += 1

    def parse_array(self):
        self.i += 1  # [
        items = []
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            self.skip_ws()
            items.append(self.parse_value())
            self.skip_ws()
            if self.i >= self.n:
                raise _Bad()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            raise _Bad()

    def parse_object(self):
        self.i += 1  # {
        obj = {}
        self.skip_ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Bad()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Bad()
            self.i += 1
            self.skip_ws()
            obj[key] = self.parse_value()
            self.skip_ws()
            if self.i >= self.n:
                raise _Bad()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _Bad()


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
        return _escape(v)
    if isinstance(v, list):
        return "[" + ",".join(_dump(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(_escape(k) + ":" + _dump(v[k]) for k in keys) + "}"
    raise _Bad()


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        p.skip_ws()
        v = p.parse_value()
        p.skip_ws()
    except _Bad:
        return "ERR"
    except RecursionError:
        return "ERR"
    if p.i != p.n:
        return "ERR"
    try:
        return _dump(v)
    except _Bad:
        return "ERR"
    except RecursionError:
        return "ERR"
