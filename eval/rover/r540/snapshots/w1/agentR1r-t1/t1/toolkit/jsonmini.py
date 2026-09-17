class _Err(Exception):
    pass


class _P:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\n\r':
            self.i += 1

    def peek(self):
        if self.i < len(self.s):
            return self.s[self.i]
        return ''

    def value(self):
        self.ws()
        c = self.peek()
        if c == '':
            raise _Err()
        if c == 'n':
            self.lit('null')
            return ('null', None)
        if c == 't':
            self.lit('true')
            return ('bool', True)
        if c == 'f':
            self.lit('false')
            return ('bool', False)
        if c == '"':
            return ('str', self.string())
        if c == '[':
            return ('arr', self.array())
        if c == '{':
            return ('obj', self.obj())
        if c == '-' or c.isdigit():
            return ('int', self.number())
        raise _Err()

    def lit(self, w):
        if self.s[self.i:self.i + len(w)] != w:
            raise _Err()
        self.i += len(w)

    def number(self):
        start = self.i
        if self.peek() == '-':
            self.i += 1
        if self.i >= len(self.s) or not self.s[self.i].isdigit():
            raise _Err()
        if self.s[self.i] == '0':
            self.i += 1
        else:
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
        if self.i < len(self.s) and self.s[self.i].isdigit():
            raise _Err()
        if self.i < len(self.s) and self.s[self.i] not in ' \t\n\r,]}:':
            raise _Err()
        return int(self.s[start:self.i])

    def string(self):
        if self.peek() != '"':
            raise _Err()
        self.i += 1
        buf = []
        while True:
            if self.i >= len(self.s):
                raise _Err()
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return ''.join(buf)
            if c == '\\':
                self.i += 1
                if self.i >= len(self.s):
                    raise _Err()
                e = self.s[self.i]
                if e == '"':
                    buf.append('"')
                elif e == '\\':
                    buf.append('\\')
                elif e == '/':
                    buf.append('/')
                elif e == 'n':
                    buf.append('\n')
                elif e == 't':
                    buf.append('\t')
                elif e == 'u':
                    if self.i + 4 >= len(self.s):
                        raise _Err()
                    h = self.s[self.i + 1:self.i + 5]
                    if len(h) != 4:
                        raise _Err()
                    for ch in h:
                        if ch not in '0123456789abcdefABCDEF':
                            raise _Err()
                    cp = int(h, 16)
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
        self.i += 1
        self.ws()
        items = []
        if self.peek() == ']':
            self.i += 1
            return items
        while True:
            items.append(self.value())
            self.ws()
            c = self.peek()
            if c == ',':
                self.i += 1
                continue
            if c == ']':
                self.i += 1
                return items
            raise _Err()

    def obj(self):
        self.i += 1
        self.ws()
        items = []
        if self.peek() == '}':
            self.i += 1
            return items
        while True:
            self.ws()
            if self.peek() != '"':
                raise _Err()
            key = self.string()
            self.ws()
            if self.peek() != ':':
                raise _Err()
            self.i += 1
            val = self.value()
            items.append((key, val))
            self.ws()
            c = self.peek()
            if c == ',':
                self.i += 1
                continue
            if c == '}':
                self.i += 1
                return items
            raise _Err()


def _esc(s):
    out = []
    for ch in s:
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        else:
            out.append(ch)
    return ''.join(out)


def _enc(v):
    t, x = v
    if t == 'null':
        return 'null'
    if t == 'bool':
        return 'true' if x else 'false'
    if t == 'int':
        return str(x)
    if t == 'str':
        return '"' + _esc(x) + '"'
    if t == 'arr':
        return '[' + ','.join(_enc(e) for e in x) + ']'
    if t == 'obj':
        d = {}
        order = []
        for k, val in x:
            if k not in d:
                order.append(k)
            d[k] = val
        order.sort()
        return '{' + ','.join('"' + _esc(k) + '":' + _enc(d[k]) for k in order) + '}'
    raise _Err()


def solve(text: str) -> str:
    p = _P(text)
    try:
        v = p.value()
        p.ws()
        if p.i != len(p.s):
            raise _Err()
        return _enc(v)
    except _Err:
        return 'ERR'
    except Exception:
        return 'ERR'
