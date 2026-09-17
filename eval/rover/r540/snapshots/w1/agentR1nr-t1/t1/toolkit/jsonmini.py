def solve(text: str) -> str:
    s = text
    n = len(s)
    i = 0

    def err():
        raise ValueError('err')

    def skip_ws():
        nonlocal i
        while i < n and s[i] in ' \t\n\r':
            i += 1

    def parse_value():
        nonlocal i
        skip_ws()
        if i >= n:
            err()
        c = s[i]
        if c == 'n':
            if s[i:i+4] == 'null':
                i += 4
                return ('raw', 'null')
            err()
        if c == 't':
            if s[i:i+4] == 'true':
                i += 4
                return ('raw', 'true')
            err()
        if c == 'f':
            if s[i:i+5] == 'false':
                i += 5
                return ('raw', 'false')
            err()
        if c == '"':
            return ('str', parse_string())
        if c == '[':
            return ('arr', parse_array())
        if c == '{':
            return ('obj', parse_object())
        if c == '-' or c.isdigit():
            return ('raw', parse_number())
        err()

    def parse_string():
        nonlocal i
        i += 1
        buf = []
        while True:
            if i >= n:
                err()
            c = s[i]
            if c == '"':
                i += 1
                return ''.join(buf)
            if c == '\\':
                i += 1
                if i >= n:
                    err()
                e = s[i]
                if e == '"':
                    buf.append('"')
                    i += 1
                elif e == '\\':
                    buf.append('\\')
                    i += 1
                elif e == '/':
                    buf.append('/')
                    i += 1
                elif e == 'n':
                    buf.append('\n')
                    i += 1
                elif e == 't':
                    buf.append('\t')
                    i += 1
                elif e == 'u':
                    h = s[i+1:i+5]
                    if len(h) != 4 or any(ch not in '0123456789abcdefABCDEF' for ch in h):
                        err()
                    cp = int(h, 16)
                    if cp < 0x20:
                        err()
                    buf.append(chr(cp))
                    i += 5
                else:
                    err()
            elif ord(c) < 0x20:
                err()
            else:
                buf.append(c)
                i += 1

    def parse_number():
        nonlocal i
        start = i
        if s[i] == '-':
            i += 1
        if i >= n or not s[i].isdigit():
            err()
        if s[i] == '0':
            i += 1
        else:
            while i < n and s[i].isdigit():
                i += 1
        num = s[start:i]
        if num == '-0':
            return '0'
        return num

    def parse_array():
        nonlocal i
        i += 1
        items = []
        skip_ws()
        if i < n and s[i] == ']':
            i += 1
            return items
        while True:
            items.append(parse_value())
            skip_ws()
            if i >= n:
                err()
            if s[i] == ',':
                i += 1
                continue
            if s[i] == ']':
                i += 1
                return items
            err()

    def parse_object():
        nonlocal i
        i += 1
        pairs = []
        skip_ws()
        if i < n and s[i] == '}':
            i += 1
            return pairs
        while True:
            skip_ws()
            if i >= n or s[i] != '"':
                err()
            key = parse_string()
            skip_ws()
            if i >= n or s[i] != ':':
                err()
            i += 1
            val = parse_value()
            pairs.append((key, val))
            skip_ws()
            if i >= n:
                err()
            if s[i] == ',':
                i += 1
                continue
            if s[i] == '}':
                i += 1
                return pairs
            err()

    def esc(cp):
        if cp == '"':
            return '\\"'
        if cp == '\\':
            return '\\\\'
        if cp == '\n':
            return '\\n'
        if cp == '\t':
            return '\\t'
        return cp

    def render(v):
        t, val = v
        if t == 'raw':
            return val
        if t == 'str':
            return '"' + ''.join(esc(ch) for ch in val) + '"'
        if t == 'arr':
            return '[' + ','.join(render(x) for x in val) + ']'
        if t == 'obj':
            m = {}
            for k, val2 in val:
                m[k] = val2
            keys = sorted(m.keys())
            return '{' + ','.join('"' + ''.join(esc(ch) for ch in k) + '":' + render(m[k]) for k in keys) + '}'
        err()

    try:
        if s == '' or s.strip() == '':
            err()
        v = parse_value()
        skip_ws()
        if i != n:
            err()
        return render(v)
    except Exception:
        return 'ERR'
