"""json_mini subcommand: strict minimal JSON parser with canonical output."""

WS = " \t\n\r"


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def fail(self):
        raise _Err()

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in WS:
            self.i += 1

    def at_end(self):
        return self.i >= self.n

    def parse_value(self):
        if self.at_end():
            self.fail()
        c = self.s[self.i]
        if c == '"':
            return ("str", self.parse_string())
        if c == "{":
            return ("obj", self.parse_object())
        if c == "[":
            return ("arr", self.parse_array())
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
            return ("int", self.parse_int())
        self.fail()

    def expect_lit(self, lit):
        if self.s[self.i:self.i + len(lit)] != lit:
            self.fail()
        self.i += len(lit)

    def parse_string(self):
        # assumes s[i] == '"'
        self.i += 1
        buf = []
        while True:
            if self.at_end():
                self.fail()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.at_end():
                    self.fail()
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
                    if self.i + 4 >= self.n:
                        self.fail()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4 or any(ch not in "0123456789abcdefABCDEF" for ch in hexs):
                        self.fail()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        self.fail()
                    buf.append(chr(cp))
                    self.i += 4
                else:
                    self.fail()
                self.i += 1
                continue
            if ord(c) < 0x20:
                self.fail()
            buf.append(c)
            self.i += 1

    def parse_int(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.at_end() or not self.s[self.i].isdigit():
                self.fail()
        if self.s[self.i] == "0":
            self.i += 1
            if not self.at_end() and self.s[self.i].isdigit():
                self.fail()
        else:
            if not self.s[self.i].isdigit():
                self.fail()
            while not self.at_end() and self.s[self.i].isdigit():
                self.i += 1
        return int(self.s[start:self.i])

    def parse_array(self):
        self.i += 1
        items = []
        self.skip_ws()
        if not self.at_end() and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            self.skip_ws()
            items.append(self.parse_value())
            self.skip_ws()
            if self.at_end():
                self.fail()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            self.fail()

    def parse_object(self):
        self.i += 1
        items = []
        self.skip_ws()
        if not self.at_end() and self.s[self.i] == "}":
            self.i += 1
            return items
        while True:
            self.skip_ws()
            if self.at_end() or self.s[self.i] != '"':
                self.fail()
            key = self.parse_string()
            self.skip_ws()
            if self.at_end() or self.s[self.i] != ":":
                self.fail()
            self.i += 1
            self.skip_ws()
            val = self.parse_value()
            items.append((key, val))
            self.skip_ws()
            if self.at_end():
                self.fail()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return items
            self.fail()


def _escape(s):
    out = []
    for c in s:
        if c == '"':
            out.append('\\"')
        elif c == "\\":
            out.append("\\\\")
        elif c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        else:
            out.append(c)
    return "".join(out)


def _render(node):
    kind, val = node
    if kind == "null":
        return "null"
    if kind == "bool":
        return "true" if val else "false"
    if kind == "int":
        return str(val)
    if kind == "str":
        return '"' + _escape(val) + '"'
    if kind == "arr":
        return "[" + ",".join(_render(x) for x in val) + "]"
    if kind == "obj":
        merged = {}
        for k, v in val:
            merged[k] = v
        parts = []
        for k in sorted(merged, key=lambda x: [ord(ch) for ch in x]):
            parts.append('"' + _escape(k) + '":' + _render(merged[k]))
        return "{" + ",".join(parts) + "}"
    raise _Err()


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        p.skip_ws()
        if p.at_end():
            return "ERR"
        node = p.parse_value()
        p.skip_ws()
        if not p.at_end():
            return "ERR"
        return _render(node)
    except _Err:
        return "ERR"
    except RecursionError:
        return "ERR"
