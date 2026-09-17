r"""Minimal JSON parser with canonical, whitespace-free output.

``solve(text)`` accepts a single JSON value (possibly surrounded by
whitespace) and returns its canonical serialization, or the single line
``ERR`` if the input is invalid.
"""


class _Error(Exception):
    pass


_WS = " \t\n\r"
_HEX = "0123456789abcdefABCDEF"


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0
        self.n = len(text)

    def parse(self):
        self._skip_ws()
        if self.i >= self.n:
            raise _Error("empty input")
        value = self._value()
        self._skip_ws()
        if self.i != self.n:
            raise _Error("trailing content")
        return value

    def _skip_ws(self):
        s = self.s
        n = self.n
        i = self.i
        while i < n and s[i] in _WS:
            i += 1
        self.i = i

    def _peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ""

    def _value(self):
        c = self._peek()
        if c == "{":
            return self._object()
        if c == "[":
            return self._array()
        if c == '"':
            return self._string()
        if c == "t":
            return self._literal("true", True)
        if c == "f":
            return self._literal("false", False)
        if c == "n":
            return self._literal("null", None)
        if c == "-" or ("0" <= c <= "9"):
            return self._number()
        raise _Error("unexpected character")

    def _literal(self, word, value):
        if self.s[self.i:self.i + len(word)] != word:
            raise _Error("bad literal")
        self.i += len(word)
        return value

    def _object(self):
        self.i += 1
        obj = {}
        self._skip_ws()
        if self._peek() == "}":
            self.i += 1
            return obj
        while True:
            self._skip_ws()
            if self._peek() != '"':
                raise _Error("bad key")
            key = self._string()
            self._skip_ws()
            if self._peek() != ":":
                raise _Error("missing colon")
            self.i += 1
            self._skip_ws()
            obj[key] = self._value()
            self._skip_ws()
            c = self._peek()
            if c == ",":
                self.i += 1
                continue
            if c == "}":
                self.i += 1
                return obj
            raise _Error("bad object separator")

    def _array(self):
        self.i += 1
        arr = []
        self._skip_ws()
        if self._peek() == "]":
            self.i += 1
            return arr
        while True:
            self._skip_ws()
            arr.append(self._value())
            self._skip_ws()
            c = self._peek()
            if c == ",":
                self.i += 1
                continue
            if c == "]":
                self.i += 1
                return arr
            raise _Error("bad array separator")

    def _string(self):
        self.i += 1
        s = self.s
        n = self.n
        chars = []
        while True:
            if self.i >= n:
                raise _Error("unterminated string")
            c = s[self.i]
            if c == '"':
                self.i += 1
                return "".join(chars)
            if c == "\\":
                self.i += 1
                if self.i >= n:
                    raise _Error("bad escape")
                e = s[self.i]
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
                    if self.i + 4 >= n:
                        raise _Error("bad unicode escape")
                    h = s[self.i + 1:self.i + 5]
                    for ch in h:
                        if ch not in _HEX:
                            raise _Error("bad unicode escape")
                    code = int(h, 16)
                    if code < 0x20:
                        raise _Error("control character")
                    chars.append(chr(code))
                    self.i += 4
                else:
                    raise _Error("bad escape")
                self.i += 1
                continue
            if c in _WS:
                raise _Error("raw control character")
            chars.append(c)
            self.i += 1

    def _number(self):
        s = self.s
        n = self.n
        start = self.i
        if s[self.i] == "-":
            self.i += 1
        if self.i >= n:
            raise _Error("bad number")
        c = s[self.i]
        if c == "0":
            self.i += 1
        elif "1" <= c <= "9":
            self.i += 1
            while self.i < n and "0" <= s[self.i] <= "9":
                self.i += 1
        else:
            raise _Error("bad number")
        if self.i < n:
            c = s[self.i]
            if "0" <= c <= "9":
                raise _Error("leading zero")
            if c == "." or c == "e" or c == "E":
                raise _Error("unsupported number form")
        token = s[start:self.i]
        value = int(token)
        if value == 0:
            return 0
        return value


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
    return "".join(out)


def _dump(value, out):
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, str):
        out.append('"' + _escape(value) + '"')
    elif isinstance(value, list):
        out.append("[")
        first = True
        for item in value:
            if not first:
                out.append(",")
            first = False
            _dump(item, out)
        out.append("]")
    elif isinstance(value, dict):
        out.append("{")
        first = True
        for key in sorted(value):
            if not first:
                out.append(",")
            first = False
            out.append('"' + _escape(key) + '":')
            _dump(value[key], out)
        out.append("}")
    else:
        raise _Error("unsupported value")


def solve(text):
    try:
        value = _Parser(text).parse()
    except _Error:
        return "ERR"
    except Exception:
        return "ERR"
    out = []
    try:
        _dump(value, out)
    except _Error:
        return "ERR"
    return "".join(out)
