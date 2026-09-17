"""json_mini subcommand: a strict JSON parser + canonical compact printer.

Input is an entire JSON value (may have leading/trailing whitespace).
Supported: null / true / false / decimal integers (optional minus, no leading
zeros, "-0" -> 0) / strings / arrays / objects (string keys).
Strings allow only these hex-standard escapes: \\" \\\\ \\/ \\n \\t \\uXXXX.
\\uXXXX decodes to the code point (must be >= 0x20). Objects allow duplicate
keys; later overrides earlier.
Output: canonical text with NO whitespace. Strings re-escape quote, backslash,
newline and tab; all other characters are literal. Object keys sorted by
Unicode code point. Any invalid input -> a single line "ERR".
"""


class _JsonError(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def _ws(self):
        s = self.s
        while self.i < len(s) and s[self.i] in " \t\n\r":
            self.i += 1

    def value(self):
        self._ws()
        if self.i >= len(self.s):
            raise _JsonError()
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
            return self.string()
        if c == "[":
            return self.array()
        if c == "{":
            return self.object()
        if c == "-" or c.isdigit():
            return self.number()
        raise _JsonError()

    def _lit(self, word):
        if self.s[self.i:self.i + len(word)] != word:
            raise _JsonError()
        self.i += len(word)

    def string(self):
        s = self.s
        if s[self.i] != '"':
            raise _JsonError()
        self.i += 1
        buf = []
        while True:
            if self.i >= len(s):
                raise _JsonError()
            c = s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if c == "\\":
                self.i += 1
                if self.i >= len(s):
                    raise _JsonError()
                e = s[self.i]
                if e == '"':
                    buf.append('"')
                    self.i += 1
                elif e == "\\":
                    buf.append("\\")
                    self.i += 1
                elif e == "/":
                    buf.append("/")
                    self.i += 1
                elif e == "n":
                    buf.append("\n")
                    self.i += 1
                elif e == "t":
                    buf.append("\t")
                    self.i += 1
                elif e == "u":
                    if self.i + 4 >= len(s):
                        raise _JsonError()
                    hexs = s[self.i + 1:self.i + 5]
                    if len(hexs) != 4:
                        raise _JsonError()
                    for ch in hexs:
                        if ch not in "0123456789abcdefABCDEF":
                            raise _JsonError()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _JsonError()
                    buf.append(chr(cp))
                    self.i += 5
                else:
                    raise _JsonError()
            elif ord(c) < 0x20:
                raise _JsonError()
            else:
                buf.append(c)
                self.i += 1

    def number(self):
        s = self.s
        start = self.i
        if s[self.i] == "-":
            self.i += 1
            if self.i >= len(s):
                raise _JsonError()
        if not s[self.i].isdigit():
            raise _JsonError()
        if s[self.i] == "0":
            self.i += 1
            if self.i < len(s) and s[self.i].isdigit():
                raise _JsonError()
        else:
            while self.i < len(s) and s[self.i].isdigit():
                self.i += 1
        if self.i < len(s) and s[self.i] in ".eE":
            raise _JsonError()
        return int(s[start:self.i])

    def array(self):
        self.i += 1  # '['
        self._ws()
        items = []
        if self.i < len(self.s) and self.s[self.i] == "]":
            self.i += 1
            return items
        while True:
            items.append(self.value())
            self._ws()
            if self.i >= len(self.s):
                raise _JsonError()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return items
            raise _JsonError()

    def object(self):
        self.i += 1  # '{'
        self._ws()
        obj = {}
        if self.i < len(self.s) and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self._ws()
            if self.i >= len(self.s) or self.s[self.i] != '"':
                raise _JsonError()
            key = self.string()
            self._ws()
            if self.i >= len(self.s) or self.s[self.i] != ":":
                raise _JsonError()
            self.i += 1
            val = self.value()
            obj[key] = val
            self._ws()
            if self.i >= len(self.s):
                raise _JsonError()
            c = self.s[self.i]
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _JsonError()


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
        parts = []
        for k in sorted(v.keys()):
            parts.append(_escape(k) + ":" + _dump(v[k]))
        return "{" + ",".join(parts) + "}"
    raise _JsonError()


def solve(text: str) -> str:
    try:
        p = _Parser(text)
        val = p.value()
        p._ws()
        if p.i != len(p.s):
            raise _JsonError()
        return _dump(val)
    except (_JsonError, IndexError, ValueError):
        return "ERR"
