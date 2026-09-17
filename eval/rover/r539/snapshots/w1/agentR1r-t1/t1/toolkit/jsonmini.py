def _decode_string(s, i):
    """Decode a JSON string starting at s[i] == '"'. Return (text, next_index) or None."""
    if i >= len(s) or s[i] != '"':
        return None
    i += 1
    buf = []
    while True:
        if i >= len(s):
            return None
        c = s[i]
        if c == '"':
            return (''.join(buf), i + 1)
        if c == '\\':
            i += 1
            if i >= len(s):
                return None
            e = s[i]
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
                if i + 4 >= len(s):
                    return None
                h = s[i + 1:i + 5]
                if len(h) != 4:
                    return None
                for ch in h:
                    if ch not in '0123456789abcdefABCDEF':
                        return None
                cp = int(h, 16)
                if cp < 0x20:
                    return None
                buf.append(chr(cp))
                i += 4
            else:
                return None
            i += 1
        else:
            if ord(c) < 0x20:
                return None
            buf.append(c)
            i += 1


def _parse_value(s, i):
    if i >= len(s):
        return None
    c = s[i]
    if c == '"':
        return _decode_string(s, i)
    if c == 'n':
        if s[i:i + 4] == 'null':
            return (None, i + 4)
        return None
    if c == 't':
        if s[i:i + 4] == 'true':
            return (True, i + 4)
        return None
    if c == 'f':
        if s[i:i + 5] == 'false':
            return (False, i + 5)
        return None
    if c == '[':
        i += 1
        arr = []
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ']':
            return (arr, i + 1)
        while True:
            r = _parse_value(s, i)
            if r is None:
                return None
            v, i = r
            arr.append(v)
            i = _skip_ws(s, i)
            if i >= len(s):
                return None
            if s[i] == ',':
                i = _skip_ws(s, i + 1)
                continue
            if s[i] == ']':
                return (arr, i + 1)
            return None
    if c == '{':
        i += 1
        obj = {}
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == '}':
            return (obj, i + 1)
        while True:
            kr = _decode_string(s, i)
            if kr is None:
                return None
            key, i = kr
            i = _skip_ws(s, i)
            if i >= len(s) or s[i] != ':':
                return None
            i = _skip_ws(s, i + 1)
            r = _parse_value(s, i)
            if r is None:
                return None
            v, i = r
            obj[key] = v
            i = _skip_ws(s, i)
            if i >= len(s):
                return None
            if s[i] == ',':
                i = _skip_ws(s, i + 1)
                continue
            if s[i] == '}':
                return (obj, i + 1)
            return None
    if c == '-' or c.isdigit():
        j = i
        if s[j] == '-':
            j += 1
        if j >= len(s) or not s[j].isdigit():
            return None
        if s[j] == '0':
            j += 1
        else:
            while j < len(s) and s[j].isdigit():
                j += 1
        return (int(s[i:j]), j)
    return None


def _skip_ws(s, i):
    while i < len(s) and s[i] in ' \t\n\r':
        i += 1
    return i


def _enc_string(x):
    buf = ['"']
    for ch in x:
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
    return ''.join(buf)


def _enc(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _enc_string(v)
    if isinstance(v, list):
        return '[' + ','.join(_enc(x) for x in v) + ']'
    if isinstance(v, dict):
        keys = sorted(v.keys())
        return '{' + ','.join(_enc_string(k) + ':' + _enc(v[k]) for k in keys) + '}'
    return 'ERR'


def solve(text: str) -> str:
    s = text
    i = _skip_ws(s, 0)
    if i >= len(s):
        return 'ERR'
    r = _parse_value(s, i)
    if r is None:
        return 'ERR'
    v, i = r
    i = _skip_ws(s, i)
    if i != len(s):
        return 'ERR'
    return _enc(v)
