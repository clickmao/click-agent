class _Err(Exception):
    pass


def _parse(s, i):
    i = _skip_ws(s, i)
    if i >= len(s):
        raise _Err()
    c = s[i]
    if c == 'n':
        if s[i:i + 4] == 'null':
            return (None, i + 4)
        raise _Err()
    if c == 't':
        if s[i:i + 4] == 'true':
            return (True, i + 4)
        raise _Err()
    if c == 'f':
        if s[i:i + 5] == 'false':
            return (False, i + 5)
        raise _Err()
    if c == '"':
        return _parse_str(s, i)
    if c == '[':
        return _parse_arr(s, i)
    if c == '{':
        return _parse_obj(s, i)
    if c == '-' or ('0' <= c <= '9'):
        return _parse_num(s, i)
    raise _Err()


def _skip_ws(s, i):
    while i < len(s) and s[i] in ' \t\n\r':
        i += 1
    return i


def _parse_num(s, i):
    start = i
    if s[i] == '-':
        i += 1
        if i >= len(s):
            raise _Err()
    if s[i] == '0':
        i += 1
        if i < len(s) and '0' <= s[i] <= '9':
            raise _Err()
    elif '1' <= s[i] <= '9':
        while i < len(s) and '0' <= s[i] <= '9':
            i += 1
    else:
        raise _Err()
    return (int(s[start:i]), i)


def _parse_str(s, i):
    i += 1
    res = []
    while True:
        if i >= len(s):
            raise _Err()
        c = s[i]
        if c == '"':
            return (''.join(res), i + 1)
        if c == '\\':
            i += 1
            if i >= len(s):
                raise _Err()
            e = s[i]
            if e == '"':
                res.append('"')
            elif e == '\\':
                res.append('\\')
            elif e == '/':
                res.append('/')
            elif e == 'n':
                res.append('\n')
            elif e == 't':
                res.append('\t')
            elif e == 'u':
                if i + 4 >= len(s):
                    raise _Err()
                h = s[i + 1:i + 5]
                if len(h) != 4 or any(ch not in '0123456789abcdefABCDEF' for ch in h):
                    raise _Err()
                cp = int(h, 16)
                if cp < 0x20:
                    raise _Err()
                res.append(chr(cp))
                i += 4
            else:
                raise _Err()
            i += 1
        else:
            if ord(c) < 0x20:
                raise _Err()
            res.append(c)
            i += 1


def _parse_arr(s, i):
    i += 1
    res = []
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == ']':
        return (res, i + 1)
    while True:
        v, i = _parse(s, i)
        res.append(v)
        i = _skip_ws(s, i)
        if i >= len(s):
            raise _Err()
        if s[i] == ',':
            i += 1
            continue
        if s[i] == ']':
            return (res, i + 1)
        raise _Err()


def _parse_obj(s, i):
    i += 1
    res = {}
    i = _skip_ws(s, i)
    if i < len(s) and s[i] == '}':
        return (res, i + 1)
    while True:
        i = _skip_ws(s, i)
        if i >= len(s) or s[i] != '"':
            raise _Err()
        key, i = _parse_str(s, i)
        i = _skip_ws(s, i)
        if i >= len(s) or s[i] != ':':
            raise _Err()
        i += 1
        v, i = _parse(s, i)
        res[key] = v
        i = _skip_ws(s, i)
        if i >= len(s):
            raise _Err()
        if s[i] == ',':
            i += 1
            continue
        if s[i] == '}':
            return (res, i + 1)
        raise _Err()


def _enc_str(x):
    out = ['"']
    for c in x:
        if c == '"':
            out.append('\\"')
        elif c == '\\':
            out.append('\\\\')
        elif c == '\n':
            out.append('\\n')
        elif c == '\t':
            out.append('\\t')
        else:
            out.append(c)
    out.append('"')
    return ''.join(out)


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
        return _enc_str(v)
    if isinstance(v, list):
        return '[' + ','.join(_enc(x) for x in v) + ']'
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda kv: [ord(ch) for ch in kv[0]])
        return '{' + ','.join(_enc_str(k) + ':' + _enc(x) for k, x in items) + '}'
    raise _Err()


def solve(text: str) -> str:
    try:
        v, i = _parse(text, 0)
        i = _skip_ws(text, i)
        if i != len(text):
            raise _Err()
    except Exception:
        return 'ERR'
    try:
        return _enc(v)
    except Exception:
        return 'ERR'
