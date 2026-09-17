"""Subcommand ``json_mini``: strict, whitespace-free JSON canonicalizer."""

_HEX = "0123456789abcdefABCDEF"
_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class _JsonError(Exception):
    """Raised internally on any syntax error; converted to ``ERR``."""


class _Parser:
    __slots__ = ("text", "pos", "length")

    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def error(self):
        raise _JsonError()

    def skip_ws(self):
        text = self.text
        pos = self.pos
        n = self.length
        while pos < n and text[pos] in " \t\n\r":
            pos += 1
        self.pos = pos

    def peek(self):
        if self.pos >= self.length:
            return ""
        return self.text[self.pos]

    def parse_value(self):
        self.skip_ws()
        ch = self.peek()
        if ch == "":
            self.error()
        if ch == "{":
            return self.parse_object()
        if ch == "[":
            return self.parse_array()
        if ch == '"':
            return ("s", self.parse_string())
        if ch == "t":
            self.literal("true")
            return ("l", "true")
        if ch == "f":
            self.literal("false")
            return ("l", "false")
        if ch == "n":
            self.literal("null")
            return ("l", "null")
        if ch == "-" or ch.isdigit():
            return ("i", self.parse_number())
        self.error()

    def literal(self, word):
        if self.text[self.pos:self.pos + len(word)] != word:
            self.error()
        self.pos += len(word)

    def parse_number(self):
        text = self.text
        n = self.length
        pos = self.pos
        start = pos
        if pos < n and text[pos] == "-":
            pos += 1
        if pos >= n or not text[pos].isdigit():
            self.error()
        if text[pos] == "0":
            pos += 1
            if pos < n and text[pos].isdigit():
                self.error()
        else:
            while pos < n and text[pos].isdigit():
                pos += 1
        self.pos = pos
        value = int(text[start:pos])
        if value == 0:
            value = 0
        return value

    def parse_string(self):
        text = self.text
        n = self.length
        pos = self.pos + 1
        chars = []
        while True:
            if pos >= n:
                self.error()
            ch = text[pos]
            if ch == '"':
                pos += 1
                break
            if ch == "\\":
                pos += 1
                if pos >= n:
                    self.error()
                esc = text[pos]
                if esc == "u":
                    pos += 1
                    if pos + 4 > n:
                        self.error()
                    digits = text[pos:pos + 4]
                    for d in digits:
                        if d not in _HEX:
                            self.error()
                    code = int(digits, 16)
                    if code < 0x20:
                        self.error()
                    chars.append(chr(code))
                    pos += 4
                    continue
                if esc not in _ESCAPES:
                    self.error()
                chars.append(_ESCAPES[esc])
                pos += 1
                continue
            if ch < "\x20":
                self.error()
            chars.append(ch)
            pos += 1
        self.pos = pos
        return "".join(chars)

    def parse_array(self):
        self.pos += 1
        items = []
        self.skip_ws()
        if self.peek() == "]":
            self.pos += 1
            return ("a", items)
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            ch = self.peek()
            if ch == ",":
                self.pos += 1
                continue
            if ch == "]":
                self.pos += 1
                return ("a", items)
            self.error()

    def parse_object(self):
        self.pos += 1
        entries = {}
        self.skip_ws()
        if self.peek() == "}":
            self.pos += 1
            return ("o", entries)
        while True:
            self.skip_ws()
            if self.peek() != '"':
                self.error()
            key = self.parse_string()
            self.skip_ws()
            if self.peek() != ":":
                self.error()
            self.pos += 1
            entries[key] = self.parse_value()
            self.skip_ws()
            ch = self.peek()
            if ch == ",":
                self.pos += 1
                continue
            if ch == "}":
                self.pos += 1
                return ("o", entries)
            self.error()


def _render(node):
    kind, value = node
    if kind == "l":
        return value
    if kind == "i":
        return str(value)
    if kind == "s":
        out = ['"']
        for ch in value:
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
    if kind == "a":
        return "[" + ",".join(_render(item) for item in value) + "]"
    if kind == "o":
        keys = sorted(value.keys())
        return "{" + ",".join(_render(("s", k)) + ":" + _render(value[k]) for k in keys) + "}"
    raise _JsonError()


def solve(text):
    """Parse one JSON value from ``text`` and return canonical text or ``ERR``."""
    parser = _Parser(text)
    try:
        node = parser.parse_value()
        parser.skip_ws()
        if parser.pos != parser.length:
            return "ERR"
        return _render(node)
    except _JsonError:
        return "ERR"
    except (ValueError, IndexError, RecursionError):
        return "ERR"
