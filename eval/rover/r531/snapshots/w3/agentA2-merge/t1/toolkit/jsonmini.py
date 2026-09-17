"""json_mini subcommand.

stdin: a single JSON value (may have surrounding whitespace/newlines).
Grammar: null / true / false / decimal integer (optional '-', no leading
zeros, -0 -> 0) / string / array / object (keys are strings).
String escapes: only standard backslash escapes (quote, backslash, slash,
n, t, uXXXX); uXXXX decodes to a char whose code point must be >= 0x20.
Objects allow duplicate keys; later overrides earlier.
Output: canonical text, no whitespace at all; strings re-escape only
quote/backslash/newline/tab, other chars verbatim; object keys sorted by
Unicode code point. Example: {"a":1,"b":[2,3]}.
Illegal input (syntax error / trailing content / bad escape / bad number /
empty input) -> exactly one line "ERR".
"""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def ws(self):
        while self.i < self.n and self.s[self.i] in " \t\n\r":
            self.i += 1

    def parse_value(self):
        if self.i >= self.n:
            raise _Err()
        c = self.s[self.i]
        if c == '"':
            return self.parse_string()
        if c == "{":
            return self.parse_object()
        if c == "[":
            return self.parse_array()
        if c == "t":
            return self.lit("true", True)
        if c == "f":
            return self.lit("false", False)
        if c == "n":
            return self.lit("null", None)
        if c == "-" or c.isdigit():
            return self.parse_number()
        raise _Err()

    def lit(self, word, val):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return val
        raise _Err()

    def parse_number(self):
        start = self.i
        neg = False
        if self.s[self.i] == "-":
            neg = True
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
        digits = self.s[start:self.i]
        v = int(digits)
        if neg and v == 0:
            return 0
        return v

    def parse_string(self):
        if self.s[self.i] != '"':
            raise _Err()
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
                    if self.i + 4 >= self.n:
                        raise _Err()
                    hexs = self.s[self.i + 1:self.i + 5]
                    if len(hexs) != 4:
                        raise _Err()
                    try:
                        cp = int(hexs, 16)
                    except ValueError:
                        raise _Err()
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    self.i += 5
                    continue
                else:
                    raise _Err()
                self.i += 1
                continue
            if ord(c) < 0x20:
                raise _Err()
            buf.append(c)
            self.i += 1

    def parse_array(self):
        self.i += 1
        self.ws()
        arr = []
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return arr
        while True:
            self.ws()
            arr.append(self.parse_value())
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise _Err()

    def parse_object(self):
        self.i += 1
        self.ws()
        obj = {}
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self.ws()
            if self.i >= self.n or self.s[self.i] != '"':
                raise _Err()
            key = self.parse_string()
            self.ws()
            if self.i >= self.n or self.s[self.i] != ":":
                raise _Err()
            self.i += 1
            self.ws()
            val = self.parse_value()
            obj[key] = val
            self.ws()
            if self.i >= self.n:
                raise _Err()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _Err()


def _enc_str(s):
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


def solve(text):
    try:
        p = _Parser(text)
        p.ws()
        if p.i >= p.n:
            return "ERR"
        val = p.parse_value()
        p.ws()
        if p.i != p.n:
            return "ERR"
        return _enc(val)
    except _Err:
        return "ERR"
    except (ValueError, IndexError, RecursionError):
        return "ERR"
