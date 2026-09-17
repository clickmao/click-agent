"""json_mini subcommand: parse a restricted JSON subset, emit canonical text.

solve(text) -> str: stdin text in, stdout text out (no trailing newline).
"""

ERR = "ERR"


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def parse(self):
        val = self.value()
        self.ws()
        if self.i != self.n:
            raise _Err()
        return val

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def value(self):
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
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
            return self.string()
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        return self.number()

    def lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Err()
        self.i += len(word)

    def number(self):
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

    def string(self):
        # self.s[self.i] == '"'
        self.i += 1
        buf = []
        while True:
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    raise _Err()
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
                    if len(hexs) != 4 or any(
                        ch not in "0123456789abcdefABCDEF" for ch in hexs
                    ):
                        raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    raise _Err()
                self.i += 1
            else:
                if ord(c) < 0x20:
                    raise _Err()
                buf.append(c)
                self.i += 1

    def array(self):
        self.i += 1  # [
        out = []
        self.ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return out
        while True:
            self.ws()
            out.append(self.value())
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return out
            raise _Err()

    def obj(self):
        self.i += 1  # {
        items = {}
        self.ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return items
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            self.ws()
            items[key] = self.value()
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return items
            raise _Err()


def _emit(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        out = ['"']
        for ch in v:
            o = ord(ch)
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
    if isinstance(v, list):
        return "[" + ",".join(_emit(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(
            _emit(k) + ":" + _emit(v[k]) for k in keys
        ) + "}"
    raise _Err()


def solve(text: str) -> str:
    try:
        val = _Parser(text).parse()
        return _emit(val)
    except _Err:
        return ERR
    except Exception:
        return ERR
