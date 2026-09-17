def solve(text: str) -> str:
    s = text
    n = len(s)
    i = 0

    class Fail(Exception):
        pass

    def ws():
        nonlocal i
        while i < n and s[i] in " \t\n\r":
            i += 1

    def parse_value():
        nonlocal i
        ws()
        if i >= n:
            raise Fail()
        c = s[i]
        if c == '"':
            return parse_string()
        if c == '{':
            return parse_object()
        if c == '[':
            return parse_array()
        if c == 't':
            if s[i:i + 4] == 'true':
                i += 4
                return True
            raise Fail()
        if c == 'f':
            if s[i:i + 5] == 'false':
                i += 5
                return False
            raise Fail()
        if c == 'n':
            if s[i:i + 4] == 'null':
                i += 4
                return None
            raise Fail()
        if c == '-' or c.isdigit():
            return parse_int()
        raise Fail()

    def parse_int():
        nonlocal i
        start = i
        if i < n and s[i] == '-':
            i += 1
        if i >= n or not s[i].isdigit():
            raise Fail()
        if s[i] == '0':
            i += 1
            if i < n and s[i].isdigit():
                raise Fail()
        else:
            while i < n and s[i].isdigit():
                i += 1
        return int(s[start:i])

    esc = {'"': '"', '\\': '\\', '/': '/', 'n': '\n', 't': '\t'}

    def parse_string():
        nonlocal i
        if s[i] != '"':
            raise Fail()
        i += 1
        out = []
        while True:
            if i >= n:
                raise Fail()
            c = s[i]
            if c == '"':
                i += 1
                break
            if c == '\\':
                i += 1
                if i >= n:
                    raise Fail()
                e = s[i]
                if e == 'u':
                    i += 1
                    if i + 4 > n:
                        raise Fail()
                    hx = s[i:i + 4]
                    for ch in hx:
                        if ch not in '0123456789abcdefABCDEF':
                            raise Fail()
                    cp = int(hx, 16)
                    if cp < 0x20:
                        raise Fail()
                    out.append(chr(cp))
                    i += 4
                elif e in esc:
                    out.append(esc[e])
                    i += 1
                else:
                    raise Fail()
            else:
                if ord(c) < 0x20:
                    raise Fail()
                out.append(c)
                i += 1
        return ''.join(out)

    def parse_array():
        nonlocal i
        i += 1
        ws()
        items = []
        if i < n and s[i] == ']':
            i += 1
            return items
        while True:
            items.append(parse_value())
            ws()
            if i >= n:
                raise Fail()
            if s[i] == ',':
                i += 1
                continue
            if s[i] == ']':
                i += 1
                break
            raise Fail()
        return items

    def parse_object():
        nonlocal i
        i += 1
        ws()
        items = []
        if i < n and s[i] == '}':
            i += 1
            return items
        while True:
            ws()
            key = parse_string()
            ws()
            if i >= n or s[i] != ':':
                raise Fail()
            i += 1
            val = parse_value()
            items.append((key, val))
            ws()
            if i >= n:
                raise Fail()
            if s[i] == ',':
                i += 1
                continue
            if s[i] == '}':
                i += 1
                break
            raise Fail()
        return items

    def emit(v):
        if v is None:
            return 'null'
        if v is True:
            return 'true'
        if v is False:
            return 'false'
        if isinstance(v, int):
            return str(v)
        if isinstance(v, str):
            r = []
            for ch in v:
                if ch == '"':
                    r.append('\\"')
                elif ch == '\\':
                    r.append('\\\\')
                elif ch == '\n':
                    r.append('\\n')
                elif ch == '\t':
                    r.append('\\t')
                else:
                    r.append(ch)
            return '"' + ''.join(r) + '"'
        if isinstance(v, list):
            return '[' + ','.join(emit(x) for x in v) + ']'
        if isinstance(v, dict):
            return '{' + ','.join(emit(k) + ':' + emit(val) for k, val in v.items()) + '}'
        raise Fail()

    def dedup(items):
        d = {}
        for k, val in items:
            d[k] = val
        return {k: d[k] for k in sorted(d, key=lambda x: [ord(c) for c in x])}

    def fix(v):
        if isinstance(v, list):
            return [fix(x) for x in v]
        if isinstance(v, dict):
            return {k: fix(val) for k, val in v.items()}
        return v

    try:
        v = parse_value()
        ws()
        if i != n:
            raise Fail()
    except Fail:
        return 'ERR'
    except (IndexError, ValueError):
        return 'ERR'

    def build(v):
        if isinstance(v, list):
            if v and all(isinstance(x, tuple) and len(x) == 2 for x in v):
                return dedup(v)
            return [build(x) for x in v]
        return v

    return emit(build(v))
