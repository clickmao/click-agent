ERR = 'ERR'

WS = ' \t\n\r'
ESCAPES = {'"': '"', '\\': '\\', '/': '/', 'n': '\n', 't': '\t', 'b': '\b', 'f': '\f', 'r': '\r'}


def _encode_string(s):
    out = ['"']
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
    out.append('"')
    return ''.join(out)


def _encode(value):
    if value is None:
        return 'null'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, list):
        return '[' + ','.join(_encode(v) for v in value) + ']'
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return '{' + ','.join(_encode_string(k) + ':' + _encode(value[k]) for k in keys) + '}'
    return ERR


class _Parser:
    def __init__(self, text):
        self.text = text
        self.i = 0

    def error(self):
        raise ValueError('parse error')

    def skip_ws(self):
        while self.i < len(self.text) and self.text[self.i] in WS:
            self.i += 1

    def parse_value(self):
        self.skip_ws()
        if self.i >= len(self.text):
            self.error()
        ch = self.text[self.i]
        if ch == 'n':
            self.lit('null')
            return None
        if ch == 't':
            self.lit('true')
            return True
        if ch == 'f':
            self.lit('false')
            return False
        if ch == '"':
            return self.parse_string()
        if ch == '[':
            return self.parse_array()
        if ch == '{':
            return self.parse_object()
        if ch == '-' or ('0' <= ch <= '9'):
            return self.parse_number()
        self.error()

    def lit(self, word):
        if self.text[self.i:self.i + len(word)] != word:
            self.error()
        self.i += len(word)

    def parse_number(self):
        start = self.i
        if self.text[self.i] == '-':
            self.i += 1
        if self.i >= len(self.text) or not ('0' <= self.text[self.i] <= '9'):
            self.error()
        if self.text[self.i] == '0':
            self.i += 1
        else:
            while self.i < len(self.text) and ('0' <= self.text[self.i] <= '9'):
                self.i += 1
        token = self.text[start:self.i]
        return int(token)

    def parse_string(self):
        self.i += 1
        chars = []
        while True:
            if self.i >= len(self.text):
                self.error()
            ch = self.text[self.i]
            if ch == '"':
                self.i += 1
                return ''.join(chars)
            if ch == '\\':
                self.i += 1
                if self.i >= len(self.text):
                    self.error()
                e = self.text[self.i]
                if e == 'u':
                    if self.i + 4 >= len(self.text):
                        self.error()
                    hexs = self.text[self.i + 1:self.i + 5]
                    if len(hexs) != 4:
                        self.error()
                    for h in hexs:
                        if not (('0' <= h <= '9') or ('a' <= h <= 'f') or ('A' <= h <= 'F')):
                            self.error()
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        self.error()
                    chars.append(chr(cp))
                    self.i += 5
                else:
                    if e not in ESCAPES:
                        self.error()
                    chars.append(ESCAPES[e])
                    self.i += 1
            elif ord(ch) < 0x20:
                self.error()
            else:
                chars.append(ch)
                self.i += 1

    def parse_array(self):
        self.i += 1
        self.skip_ws()
        items = []
        if self.i < len(self.text) and self.text[self.i] == ']':
            self.i += 1
            return items
        while True:
            items.append(self.parse_value())
            self.skip_ws()
            if self.i >= len(self.text):
                self.error()
            c = self.text[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == ']':
                self.i += 1
                return items
            self.error()

    def parse_object(self):
        self.i += 1
        self.skip_ws()
        result = {}
        if self.i < len(self.text) and self.text[self.i] == '}':
            self.i += 1
            return result
        while True:
            self.skip_ws()
            if self.i >= len(self.text) or self.text[self.i] != '"':
                self.error()
            key = self.parse_string()
            self.skip_ws()
            if self.i >= len(self.text) or self.text[self.i] != ':':
                self.error()
            self.i += 1
            value = self.parse_value()
            result[key] = value
            self.skip_ws()
            if self.i >= len(self.text):
                self.error()
            c = self.text[self.i]
            if c == ',':
                self.i += 1
                continue
            if c == '}':
                self.i += 1
                return result
            self.error()


def solve(text):
    p = _Parser(text)
    try:
        v = p.parse_value()
        p.skip_ws()
        if p.i != len(text):
            return ERR
        return _encode(v)
    except Exception:
        return ERR
