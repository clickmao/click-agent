"""json_mini subcommand: parse and re-serialize JSON canonically."""


class _Err(Exception):
    pass


class _Parser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def ws(self):
        s, n = self.s, len(self.s)
        while self.i < n and s[self.i] in ' \t\n\r':
            self.i += 1

    def parse_value(self):
        self.ws()
        if self.i >= len(self.s):
            raise _Err()
        c = self.s[self.i]
        if c == '{':
            return self.parse_object()
        if c == '[':
            return self.parse_array()
        if c == '"':
            return ('s', self.parse_string())
        if c == 't':
            return self.lit('true', ('b', True))
        if c == 'f':
            return self.lit('false', ('b', False))
        if c == 'n':
            return self.lit('null', ('n', None))
        if c == '-' or c.isdigit():
            return ('i', self.parse_number())
        raise _Err()

    def lit(self, word, val):
        if self.s.startswith(word, self.i):
            self.i += len(word)
            return val
        raise _Err()

    def parse_number(self):
        s, n = self.s, len(self.s)
        start = self.i
        i = start
        if i < n and s[i] == '-':
            i += 1
        if i >= n or not s[i].isdigit():
            raise _Err()
        if s[i] == '0':
            i += 1
        else:
            while i < n and s[i].isdigit():
                i += 1
        if i < n and (s[i] == '.' or s[i] in 'eE'):
            raise _Err()
        self.i = i
        return int(s[start:i])

    def parse_string(self):
        s, n = self.s, len(self.s)
        i = self.i + 1
        buf = []
        while True:
            if i >= n:
                raise _Err()
            c = s[i]
            if c == '"':
                i += 1
                break
            if c == '\\':
                i += 1
                if i >= n:
                    raise _Err()
                e = s[i]
                if e == '"' or e == '\\' or e == '/':
                    buf.append(e)
                    i += 1
                elif e == 'n':
                    buf.append('\n')
                    i += 1
                elif e == 't':
                    buf.append('\t')
                    i += 1
                elif e == 'u':
                    if i + 4 >= n:
                        raise _Err()
                    hexs = s[i + 1:i + 5]
                    for h in hexs:
                        if h not in '0123456789abcdefABCDEF':
                            raise _Err()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise _Err()
                    buf.append(chr(cp))
                    i += 5
                else:
                    raise _Err()
            else:
                if ord(c) < 0x20:
                    raise _Err()
                buf.append(c)
                i += 1
        self.i = i
        return ''.join(buf)

    def parse_array(self):
        self.i += 1
        items = []
        self.ws()
        if self.i < len(self.s) and self.s[self.i] == ']':
            self.i += 1
            return ('a', items)
        while True:
            items.append(self.parse_value())
            self.ws()
            if self.i >= len(self.s):
                raise _Err()
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == ']':
                self.i += 1
                return ('a', items)
            raise _Err()

    def parse_object(self):
        self.i += 1
        obj = {}
        self.ws()
        if self.i < len(self.s) and self.s[self.i] == '}':
            self.i += 1
            return ('o', obj)
        while True:
            self.ws()
            if self.i >= len(self.s) or self.s[self.i] != '"':
                raise _Err()
            key = self.parse_string()
            self.ws()
            if self.i >= len(self.s) or self.s[self.i] != ':':
                raise _Err()
            self.i += 1
            val = self.parse_value()
            obj[key] = val
            self.ws()
            if self.i >= len(self.s):
                raise _Err()
            c = self.s[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == '}':
                self.i += 1
                return ('o', obj)
            raise _Err()


def _dump(v):
    t = v[0]
    if t == 'n':
        return 'null'
    if t == 'b':
        return 'true' if v[1] else 'false'
    if t == 'i':
        return str(v[1])
    if t == 's':
        out = ['"']
        for ch in v[1]:
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
        out.append('"')
        return ''.join(out)
    if t == 'a':
        return '[' + ','.join(_dump(x) for x in v[1]) + ']'
    keys = sorted(v[1].keys())
    return '{' + ','.join(_dump(('s', k)) + ':' + _dump(v[1][k]) for k in keys) + '}'


def solve(text: str) -> str:
    p = _Parser(text)
    try:
        v = p.parse_value()
        p.ws()
        if p.i != len(p.s):
            raise _Err()
    except _Err:
        return 'ERR'
    return _dump(v)
