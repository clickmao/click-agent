r"""json_mini: minimal JSON parser + canonical compact serializer.

Takes the full stdin text, returns the exact stdout text (no trailing newline).

Supported values: null / true / false / decimal integers (optional leading '-',
no leading zeros, "-0" -> 0) / strings / arrays / objects (string keys).
String escapes allowed: \" \\ \/ \n \t \uXXXX ; decoded code points must be >= 0x20.
Duplicate object keys: last one wins.
Output: compact text with no whitespace. Strings re-escape quote/backslash/newline/tab,
other characters verbatim. Object keys sorted by Unicode code point.
Invalid input (syntax error / trailing content / bad escape / bad number / empty) => "ERR".
"""


class _JsonError(Exception):
    pass


_WS = " \t\n\r"


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.n = len(s)

    def error(self):
        raise _JsonError()

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in _WS:
            self.i += 1

    def peek(self):
        if self.i >= self.n:
            return None
        return self.s[self.i]

    def parse_value(self):
        c = self.peek()
        if c is None:
            self.error()
        if c == '"':
            return self.parse_string()
        if c == "[":
            return self.parse_array()
        if c == "{":
            return self.parse_object()
        if c == "t":
            return self.parse_lit("true", True)
        if c == "f":
            return self.parse_lit("false", False)
        if c == "n":
            return self.parse_lit("null", None)
        if c == "-" or c.isdigit():
            return self.parse_number()
        self.error()

    def parse_lit(self, word, val):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return val
        self.error()

    def parse_number(self):
        start = self.i
        if self.s[self.i] == "-":
            self.i += 1
            if self.i >= self.n or not self.s[self.i].isdigit():
                self.error()
        if self.s[self.i] == "0":
            self.i += 1
        elif self.s[self.i].isdigit():
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        else:
            self.error()
        # reject fractional / exponent forms: not supported by spec
        if self.i < self.n and (self.s[self.i] == "." or self.s[self.i] in "eE"):
            self.error()
        tok = self.s[start:self.i]
        try:
            return int(tok)
        except ValueError:
            self.error()

    def parse_string(self):
        if self.s[self.i] != '"':
            self.error()
        self.i += 1
        chars = []
        while True:
            if self.i >= self.n:
                self.error()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= self.n:
                    self.error()
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
                    code = self.parse_u()
                    if code < 0x20:
                        self.error()
                    chars.append(chr(code))
                else:
                    self.error()
                self.i += 1
            elif ord(c) < 0x20:
                self.error()
            else:
                chars.append(c)
                self.i += 1

    def parse_u(self):
        # self.i points at 'u'
        if self.i + 4 >= self.n:
            self.error()
        hexs = self.s[self.i + 1:self.i + 5]
        if len(hexs) != 4:
            self.error()
        for ch in hexs:
            if ch not in "0123456789abcdefABCDEF":
                self.error()
        self.i += 4
        return int(hexs, 16)

    def parse_array(self):
        self.i += 1  # '['
        self.skip_ws()
        arr = []
        if self.peek() == "]":
            self.i += 1
            return arr
        while True:
            arr.append(self.parse_value())
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                self.skip_ws()
                continue
            if c == "]":
                self.i += 1
                return arr
            self.error()

    def parse_object(self):
        self.i += 1  # '{'
        self.skip_ws()
        obj = {}
        if self.peek() == "}":
            self.i += 1
            return obj
        while True:
            self.skip_ws()
            if self.peek() != '"':
                self.error()
            key = self.parse_string()
            self.skip_ws()
            if self.peek() != ":":
                self.error()
            self.i += 1
            self.skip_ws()
            val = self.parse_value()
            obj[key] = val
            self.skip_ws()
            c = self.peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            self.error()


def _emit(v, out):
    if v is None:
        out.append("null")
    elif v is True:
        out.append("true")
    elif v is False:
        out.append("false")
    elif isinstance(v, int):
        out.append(str(v))
    elif isinstance(v, str):
        _emit_string(v, out)
    elif isinstance(v, list):
        out.append("[")
        first = True
        for item in v:
            if not first:
                out.append(",")
            first = False
            _emit(item, out)
        out.append("]")
    elif isinstance(v, dict):
        out.append("{")
        first = True
        for key in sorted(v.keys()):
            if not first:
                out.append(",")
            first = False
            _emit_string(key, out)
            out.append(":")
            _emit(v[key], out)
        out.append("}")
    else:
        raise _JsonError()


def _emit_string(s, out):
    out.append('"')
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


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        p.skip_ws()
        if p.i >= p.n:
            return "ERR"
        val = p.parse_value()
        p.skip_ws()
        if p.i != p.n:
            return "ERR"
        out = []
        _emit(val, out)
        return "".join(out)
    except _JsonError:
        return "ERR"
    except RecursionError:
        return "ERR"
