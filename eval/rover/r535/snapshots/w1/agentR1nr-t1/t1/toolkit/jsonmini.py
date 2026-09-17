def solve(text: str) -> str:
    # mini JSON parser: no regex module escape issues; escape sequences built at runtime
    BSLASH = chr(92)
    QUOTE = chr(34)
    TAB = chr(9)
    NEWLINE = chr(10)

    n = len(text)
    i = 0

    def parse_value(pos):
        pos = skip_ws(pos)
        if pos >= n:
            raise ValueError("eof")
        c = text[pos]
        if c == '{':
            return parse_object(pos)
        if c == '[':
            return parse_array(pos)
        if c == QUOTE:
            return parse_string(pos)
        if c == '-' or c.isdigit():
            return parse_number(pos)
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if text.startswith(lit, pos):
                return (val, pos + len(lit))
        raise ValueError("bad value")

    def skip_ws(pos):
        while pos < n and text[pos] in ' \t\r\n':
            pos += 1
        return pos

    def parse_number(pos):
        start = pos
        if pos < n and text[pos] == '-':
            pos += 1
        if pos >= n or not text[pos].isdigit():
            raise ValueError("bad number")
        if text[pos] == '0':
            pos += 1
            if pos < n and text[pos].isdigit():
                raise ValueError("leading zero")
        else:
            while pos < n and text[pos].isdigit():
                pos += 1
        if pos < n and (text[pos] == '.' or text[pos] in 'eE'):
            raise ValueError("float not allowed")
        val = int(text[start:pos])
        return (val, pos)

    def parse_string(pos):
        if text[pos] != QUOTE:
            raise ValueError("expected quote")
        pos += 1
        buf = []
        while True:
            if pos >= n:
                raise ValueError("unterminated string")
            c = text[pos]
            if c == QUOTE:
                return (''.join(buf), pos + 1)
            if c == BSLASH:
                pos += 1
                if pos >= n:
                    raise ValueError("bad escape")
                e = text[pos]
                if e == QUOTE:
                    buf.append(QUOTE); pos += 1
                elif e == BSLASH:
                    buf.append(BSLASH); pos += 1
                elif e == '/':
                    buf.append('/'); pos += 1
                elif e == 'n':
                    buf.append(NEWLINE); pos += 1
                elif e == 't':
                    buf.append(TAB); pos += 1
                elif e == 'u':
                    if pos + 4 >= n:
                        raise ValueError("short unicode")
                    hexs = text[pos+1:pos+5]
                    for h in hexs:
                        if h not in '0123456789abcdefABCDEF':
                            raise ValueError("bad hex")
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise ValueError("low codepoint")
                    buf.append(chr(cp))
                    pos += 5
                else:
                    raise ValueError("bad escape char")
            else:
                if ord(c) < 0x20:
                    raise ValueError("raw control")
                buf.append(c)
                pos += 1

    def parse_array(pos):
        pos += 1
        arr = []
        pos = skip_ws(pos)
        if pos < n and text[pos] == ']':
            return (arr, pos + 1)
        while True:
            val, pos = parse_value(pos)
            arr.append(val)
            pos = skip_ws(pos)
            if pos >= n:
                raise ValueError("unterminated array")
            if text[pos] == ',':
                pos += 1
                continue
            if text[pos] == ']':
                return (arr, pos + 1)
            raise ValueError("bad array")

    def parse_object(pos):
        pos += 1
        obj = {}
        pos = skip_ws(pos)
        if pos < n and text[pos] == '}':
            return (obj, pos + 1)
        while True:
            pos = skip_ws(pos)
            if pos >= n or text[pos] != QUOTE:
                raise ValueError("bad key")
            key, pos = parse_string(pos)
            pos = skip_ws(pos)
            if pos >= n or text[pos] != ':':
                raise ValueError("expected colon")
            pos += 1
            val, pos = parse_value(pos)
            obj[key] = val
            pos = skip_ws(pos)
            if pos >= n:
                raise ValueError("unterminated object")
            if text[pos] == ',':
                pos += 1
                continue
            if text[pos] == '}':
                return (obj, pos + 1)
            raise ValueError("bad object")

    def emit(val, buf):
        if val is None:
            buf.append("null")
        elif val is True:
            buf.append("true")
        elif val is False:
            buf.append("false")
        elif isinstance(val, int):
            buf.append(str(val))
        elif isinstance(val, str):
            out = [QUOTE]
            for ch in val:
                if ch == QUOTE:
                    out.append(BSLASH + QUOTE)
                elif ch == BSLASH:
                    out.append(BSLASH + BSLASH)
                elif ch == NEWLINE:
                    out.append(BSLASH + 'n')
                elif ch == TAB:
                    out.append(BSLASH + 't')
                else:
                    out.append(ch)
            out.append(QUOTE)
            buf.append(''.join(out))
        elif isinstance(val, list):
            buf.append('[')
            for idx, item in enumerate(val):
                if idx:
                    buf.append(',')
                emit(item, buf)
            buf.append(']')
        elif isinstance(val, dict):
            buf.append('{')
            keys = sorted(val.keys())
            for idx, k in enumerate(keys):
                if idx:
                    buf.append(',')
                emit(k, buf)
                buf.append(':')
                emit(val[k], buf)
            buf.append('}')
        else:
            raise ValueError("unknown type")

    try:
        if text.strip() == '':
            return "ERR"
        val, end = parse_value(0)
        end = skip_ws(end)
        if end != n:
            return "ERR"
        buf = []
        emit(val, buf)
        return ''.join(buf)
    except Exception:
        return "ERR"
