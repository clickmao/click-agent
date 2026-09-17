_WS = ' \t\n\r'
_ESC = {'"': '"', '\\': '\\', '/': '/', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}


def _emit_string(value, buf):
    buf.append('"')
    for ch in value:
        if ch == '"':
            buf.append('\\"')
        elif ch == '\\':
            buf.append('\\\\')
        elif ch == '\n':
            buf.append('\\n')
        elif ch == '\t':
            buf.append('\\t')
        else:
            buf.append(ch)
    buf.append('"')


def _is_digit(ch):
    return len(ch) == 1 and '0' <= ch <= '9'


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in _WS:
            self.i += 1

    def parse(self):
        self.ws()
        v = self.value()
        self.ws()
        if self.i != len(self.s):
            raise ValueError('trailing')
        return v

    def value(self):
        if self.i >= len(self.s):
            raise ValueError('eof')
        c = self.s[self.i]
        if c == '{':
            return self.obj()
        if c == '[':
            return self.arr()
        if c == '"':
            return self.string()
        if self.s.startswith('true', self.i):
            self.i += 4
            return True
        if self.s.startswith('false', self.i):
            self.i += 5
            return False
        if self.s.startswith('null', self.i):
            self.i += 4
            return None
        if c == '-' or _is_digit(c):
            return self.number()
        raise ValueError('bad value')

    def number(self):
        start = self.i
        if self.s[self.i] == '-':
            self.i += 1
        if self.i >= len(self.s) or not _is_digit(self.s[self.i]):
            raise ValueError('bad number')
        if self.s[self.i] == '0':
            self.i += 1
            if self.i < len(self.s) and _is_digit(self.s[self.i]):
                raise ValueError('leading zero')
        else:
            while self.i < len(self.s) and _is_digit(self.s[self.i]):
                self.i += 1
        return int(self.s[start:self.i])

    def string(self):
        self.i += 1
        buf = []
        while True:
            if self.i >= len(self.s):
                raise ValueError('unterminated')
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return ''.join(buf)
            if c == '\\':
                self.i += 1
                if self.i >= len(self.s):
                    raise ValueError('bad escape')
                e = self.s[self.i]
                if e == 'u':
                    if self.i + 4 >= len(self.s):
                        raise ValueError('bad unicode')
                    hexs = self.s[self.i + 1:self.i + 5]
                    for h in hexs:
                        if h not in '0123456789abcdefABCDEF':
                            raise ValueError('bad unicode')
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise ValueError('control')
                    buf.append(chr(cp))
                    self.i += 5
                elif e in _ESC:
                    buf.append(_ESC[e])
                    self.i += 1
                else:
                    raise ValueError('bad escape')
            elif ord(c) < 0x20:
                raise ValueError('raw control')
            else:
                buf.append(c)
                self.i += 1

    def arr(self):
        self.i += 1
        self.ws()
        items = []
        if self.i < len(self.s) and self.s[self.i] == ']':
            self.i += 1
            return items
        while True:
            items.append(self.value())
            self.ws()
            if self.i >= len(self.s):
                raise ValueError('unterminated array')
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                self.ws()
            elif c == ']':
                self.i += 1
                return items
            else:
                raise ValueError('bad array')

    def obj(self):
        self.i += 1
        self.ws()
        pairs = {}
        if self.i < len(self.s) and self.s[self.i] == '}':
            self.i += 1
            return pairs
        while True:
            if self.i >= len(self.s) or self.s[self.i] != '"':
                raise ValueError('bad key')
            k = self.string()
            self.ws()
            if self.i >= len(self.s) or self.s[self.i] != ':':
                raise ValueError('missing colon')
            self.i += 1
            self.ws()
            pairs[k] = self.value()
            self.ws()
            if self.i >= len(self.s):
                raise ValueError('unterminated object')
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                self.ws()
            elif c == '}':
                self.i += 1
                return pairs
            else:
                raise ValueError('bad object')


def _dump(value, buf):
    if value is None:
        buf.append('null')
    elif value is True:
        buf.append('true')
    elif value is False:
        buf.append('false')
    elif isinstance(value, int):
        buf.append(str(value))
    elif isinstance(value, str):
        _emit_string(value, buf)
    elif isinstance(value, list):
        buf.append('[')
        for i, item in enumerate(value):
            if i:
                buf.append(',')
            _dump(item, buf)
        buf.append(']')
    else:
        buf.append('{')
        for i, k in enumerate(sorted(value.keys())):
            if i:
                buf.append(',')
            _emit_string(k, buf)
            buf.append(':')
            _dump(value[k], buf)
        buf.append('}')


def solve(text: str) -> str:
    try:
        value = _Parser(text).parse()
    except (ValueError, IndexError, RecursionError):
        return 'ERR'
    buf = []
    _dump(value, buf)
    return ''.join(buf)
