"""json_mini subcommand: a strict mini JSON parser producing canonical text.

solve(text) -> stdout text (no trailing newline).
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def error(self):
        raise _Err()

    def skip_ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n\r":
            self.i += 1

    def parse_value(self):
        if self.i >= len(self.s):
            self.error()
        c = self.s[self.i]
        if c == "n":
            self.expect_word("null")
            return None
        if c == "t":
            self.expect_word("true")
            return True
        if c == "f":
            self.expect_word("false")
            return False
        if c == '"':
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "-" or c.isdigit():
            return self.parse_number()
        self.error()

    def expect_word(self, w):
        if self.s[self.i:self.i + len(w)] != w:
            self.error()
        self.i += len(w)

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.i >= len(self.s):
                self.error()
        if not self.s[self.i].isdigit():
            self.error()
        if self.s[self.i] == "0":
            self.i += 1
            # no leading zeros
            if self.i < len(self.s) and self.s[self.i].isdigit():
                self.error()
        else:
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
        return int(self.s[start:self.i])

    def parse_string(self):
        if self.s[self.i] != '"':
            self.error()
        self.i += 1
        chars = []
        while True:
            if self.i >= len(self.s):
                self.error()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= len(self.s):
                    self.error()
                e = self.s[self.i]
                self.i += 1
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
                    if self.i + 4 > len(self.s):
                        self.error()
                    hx = self.s[self.i:self.i + 4]
                    for ch in hx:
                        if ch not in "0123456789abcdefABCDEF":
                            self.error()
                    self.i += 4
                    cp = int(hx, 16)
                    if cp < 0x20:
                        self.error()
                    chars.append(chr(cp))
                else:
                    self.error()
            else:
                if c == "\x00":
                    self.error()
                if ord(c) < 0x20:
                    self.error()
                chars.append(c)
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
                self.error()
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == "]":
                self.i += 1
                return arr
            self.error()

    def parse_object(self):
        self.i += 1  # {
        obj = {}
        self.skip_ws()
        if self.i < len(self.s) and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self.skip_ws()
            if self.i >= len(self.s) or self.s[self.i] != '"':
                self.error()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= len(self.s) or self.s[self.i] != ":":
                self.error()
            self.i += 1
            self.skip_ws()
            val = self.parse_value()
            obj[key] = val
            self.skip_ws()
            if self.i >= len(self.s):
                self.error()
            if self.s[self.i] == ",":
                self.i += 1
                continue
            if self.s[self.i] == "}":
                self.i += 1
                return obj
            self.error()


def _enc_str(s):
    out = ['"']
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
    out.append('"')
    return "".join(out)


def _enc(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _enc_str(v)
    if isinstance(v, list):
        return "[" + ",".join(_enc(x) for x in v) + "]"
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return "{" + ",".join(_enc_str(k) + ":" + _enc(v[k]) for k in keys) + "}"
    raise _Err()


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        p.skip_ws()
        if p.i >= len(text):
            return "ERR"
        v = p.parse_value()
        p.skip_ws()
        if p.i != len(text):
            return "ERR"
        return _enc(v)
    except _Err:
        return "ERR"
    except Exception:
        return "ERR"
