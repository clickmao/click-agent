def solve(text: str) -> str:
    s = text
    n = len(s)
    i = 0

    def skip_ws():
        nonlocal i
        while i < n and s[i] in ' \t\n\r':
            i += 1

    def parse_value():
        nonlocal i
        skip_ws()
        if i >= n:
            raise ValueError('unexpected end')
        c = s[i]
        if c == 'n':
            for ch in 'null':
                if i >= n or s[i] != ch:
                    raise ValueError('bad null')
                i += 1
            return 'null'
        if c == 't':
            for ch in 'true':
                if i >= n or s[i] != ch:
                    raise ValueError('bad true')
                i += 1
            return 'true'
        if c == 'f':
            for ch in 'false':
                if i >= n or s[i] != ch:
                    raise ValueError('bad false')
                i += 1
            return 'false'
        if c == '"':
            return parse_string()
        if c == '[':
            return parse_array()
        if c == '{':
            return parse_object()
        if c == '-' or c.isdigit():
            return parse_number()
        raise ValueError('unexpected char')

    def parse_string():
        nonlocal i
        if s[i] != '"':
            raise ValueError('expect quote')
        i += 1
        out = []
        while True:
            if i >= n:
                raise ValueError('unterminated string')
            c = s[i]
            if c == '"':
                i += 1
                break
            if c == '\\':
                i += 1
                if i >= n:
                    raise ValueError('bad escape')
                e = s[i]
                if e == '"':
                    out.append('"')
                    i += 1
                elif e == '\\':
                    out.append('\\')
                    i += 1
                elif e == '/':
                    out.append('/')
                    i += 1
                elif e == 'n':
                    out.append('\n')
                    i += 1
                elif e == 't':
                    out.append('\t')
                    i += 1
                elif e == 'u':
                    i += 1
                    if i + 4 > n:
                        raise ValueError('bad u escape')
                    hx = s[i:i+4]
                    for ch in hx:
                        if ch not in '0123456789abcdefABCDEF':
                            raise ValueError('bad hex')
                    cp = int(hx, 16)
                    i += 4
                    if cp < 0x20:
                        raise ValueError('control char')
                    out.append(chr(cp))
                else:
                    raise ValueError('bad escape')
            else:
                if ord(c) < 0x20:
                    raise ValueError('control char')
                out.append(c)
                i += 1
        return '"' + ''.join(escape_char(ch) for ch in out) + '"'

    def escape_char(ch):
        if ch == '"':
            return '\\"'
        if ch == '\\':
            return '\\\\'
        if ch == '\n':
            return '\\n'
        if ch == '\t':
            return '\\t'
        return ch

    def parse_number():
        nonlocal i
        start = i
        neg = False
        if s[i] == '-':
            neg = True
            i += 1
            if i >= n or not s[i].isdigit():
                raise ValueError('bad number')
        if s[i] == '0':
            i += 1
        elif s[i].isdigit():
            while i < n and s[i].isdigit():
                i += 1
        else:
            raise ValueError('bad number')
        num = int(s[start:i])
        return str(num)

    def parse_array():
        nonlocal i
        i += 1
        items = []
        skip_ws()
        if i < n and s[i] == ']':
            i += 1
            return '[]'
        while True:
            items.append(parse_value())
            skip_ws()
            if i >= n:
                raise ValueError('unterminated array')
            if s[i] == ',':
                i += 1
                continue
            if s[i] == ']':
                i += 1
                break
            raise ValueError('bad array')
        return '[' + ','.join(items) + ']'

    def parse_object():
        nonlocal i
        i += 1
        pairs = {}
        skip_ws()
        if i < n and s[i] == '}':
            i += 1
            return '{}'
        while True:
            skip_ws()
            if i >= n or s[i] != '"':
                raise ValueError('expect key')
            key = parse_string()
            skip_ws()
            if i >= n or s[i] != ':':
                raise ValueError('expect colon')
            i += 1
            val = parse_value()
            pairs[key[1:-1]] = (key, val)
            skip_ws()
            if i >= n:
                raise ValueError('unterminated object')
            if s[i] == ',':
                i += 1
                continue
            if s[i] == '}':
                i += 1
                break
            raise ValueError('bad object')
        keys = sorted(pairs.keys())
        parts = []
        for k in keys:
            kk, vv = pairs[k]
            parts.append(kk + ':' + vv)
        return '{' + ','.join(parts) + '}'

    try:
        skip_ws()
        if i >= n:
            return 'ERR'
        val = parse_value()
        skip_ws()
        if i != n:
            return 'ERR'
        return val
    except (ValueError, IndexError):
        return 'ERR'
    except RecursionError:
        return 'ERR'
