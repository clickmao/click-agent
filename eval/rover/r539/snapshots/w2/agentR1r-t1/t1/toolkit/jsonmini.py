def solve(text: str) -> str:
    s = text
    n = len(s)
    pos = [0]

    class Bad(Exception):
        pass

    def skip_ws():
        while pos[0] < n and s[pos[0]] in ' \t\r\n':
            pos[0] += 1

    def parse_value():
        skip_ws()
        if pos[0] >= n:
            raise Bad()
        c = s[pos[0]]
        if c == 'n':
            if s[pos[0]:pos[0]+4] == 'null':
                pos[0] += 4
                return 'null'
            raise Bad()
        if c == 't':
            if s[pos[0]:pos[0]+4] == 'true':
                pos[0] += 4
                return 'true'
            raise Bad()
        if c == 'f':
            if s[pos[0]:pos[0]+5] == 'false':
                pos[0] += 5
                return 'false'
            raise Bad()
        if c == '"':
            return '"' + parse_string() + '"'
        if c == '[':
            return parse_array()
        if c == '{':
            return parse_object()
        if c == '-' or c.isdigit():
            return parse_number()
        raise Bad()

    def parse_number():
        start = pos[0]
        if s[pos[0]] == '-':
            pos[0] += 1
        if pos[0] >= n or not s[pos[0]].isdigit():
            raise Bad()
        if s[pos[0]] == '0':
            pos[0] += 1
        else:
            while pos[0] < n and s[pos[0]].isdigit():
                pos[0] += 1
        val = s[start:pos[0]]
        v = int(val)
        return str(v)

    def parse_string():
        # pos at opening quote
        pos[0] += 1
        buf = []
        while True:
            if pos[0] >= n:
                raise Bad()
            c = s[pos[0]]
            if c == '"':
                pos[0] += 1
                break
            if c == '\\':
                pos[0] += 1
                if pos[0] >= n:
                    raise Bad()
                e = s[pos[0]]
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
                    hexs = s[pos[0]+1:pos[0]+5]
                    if len(hexs) != 4:
                        raise Bad()
                    try:
                        cp = int(hexs, 16)
                    except ValueError:
                        raise Bad()
                    if hexs != hexs:
                        raise Bad()
                    if cp < 0x20:
                        raise Bad()
                    buf.append(chr(cp))
                    pos[0] += 4
                else:
                    raise Bad()
                pos[0] += 1
                continue
            if ord(c) < 0x20:
                raise Bad()
            buf.append(c)
            pos[0] += 1
        return ''.join(buf)

    def parse_array():
        pos[0] += 1
        items = []
        skip_ws()
        if pos[0] < n and s[pos[0]] == ']':
            pos[0] += 1
            return '[]'
        while True:
            items.append(parse_value())
            skip_ws()
            if pos[0] >= n:
                raise Bad()
            if s[pos[0]] == ',':
                pos[0] += 1
                continue
            if s[pos[0]] == ']':
                pos[0] += 1
                break
            raise Bad()
        return '[' + ','.join(items) + ']'

    def parse_object():
        pos[0] += 1
        pairs = []
        skip_ws()
        if pos[0] < n and s[pos[0]] == '}':
            pos[0] += 1
            return '{}'
        while True:
            skip_ws()
            if pos[0] >= n or s[pos[0]] != '"':
                raise Bad()
            key_raw = parse_string()
            skip_ws()
            if pos[0] >= n or s[pos[0]] != ':':
                raise Bad()
            pos[0] += 1
            val = parse_value()
            pairs.append((key_raw, val))
            skip_ws()
            if pos[0] >= n:
                raise Bad()
            if s[pos[0]] == ',':
                pos[0] += 1
                continue
            if s[pos[0]] == '}':
                pos[0] += 1
                break
            raise Bad()
        order = {}
        for i, (k, v) in enumerate(pairs):
            order[k] = (i, v)
        keys = sorted(order.keys())
        parts = []
        for k in keys:
            parts.append(escape_str(k) + ':' + order[k][1])
        return '{' + ','.join(parts) + '}'

    def escape_str(raw):
        parts = []
        for ch in raw:
            if ch == '"':
                parts.append('\\"')
            elif ch == '\\':
                parts.append('\\\\')
            elif ch == '\n':
                parts.append('\\n')
            elif ch == '\t':
                parts.append('\\t')
            else:
                parts.append(ch)
        return '"' + ''.join(parts) + '"'

    raw_parsed = None
    try:
        raw_parsed = parse_value()
        skip_ws()
        if pos[0] != n:
            return 'ERR'
    except Bad:
        return 'ERR'
    except (ValueError, IndexError, RecursionError):
        return 'ERR'
    # re-escape all strings: top-level strings were emitted raw-escaped with original escapes;
    # re-serialize fully instead
    return _normalize(text)


def _normalize(text):
    # full re-parse with proper string handling for output escaping
    pos = [0]
    n = len(text)

    class Bad(Exception):
        pass

    def skip_ws():
        while pos[0] < n and text[pos[0]] in ' \t\r\n':
            pos[0] += 1

    def esc(raw):
        out = []
        for ch in raw:
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
        return '"' + ''.join(out) + '"'

    def pstr():
        pos[0] += 1
        buf = []
        while True:
            if pos[0] >= n:
                raise Bad()
            c = text[pos[0]]
            if c == '"':
                pos[0] += 1
                return ''.join(buf)
            if c == '\\':
                pos[0] += 1
                if pos[0] >= n:
                    raise Bad()
                e = text[pos[0]]
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
                    h = text[pos[0]+1:pos[0]+5]
                    if len(h) != 4 or any(ch not in '0123456789abcdefABCDEF' for ch in h):
                        raise Bad()
                    cp = int(h, 16)
                    if cp < 0x20:
                        raise Bad()
                    buf.append(chr(cp))
                    pos[0] += 4
                else:
                    raise Bad()
                pos[0] += 1
                continue
            if ord(c) < 0x20:
                raise Bad()
            buf.append(c)
            pos[0] += 1

    def pval():
        skip_ws()
        if pos[0] >= n:
            raise Bad()
        c = text[pos[0]]
        if c == 'n':
            if text[pos[0]:pos[0]+4] != 'null':
                raise Bad()
            pos[0] += 4
            return 'null'
        if c == 't':
            if text[pos[0]:pos[0]+4] != 'true':
                raise Bad()
            pos[0] += 4
            return 'true'
        if c == 'f':
            if text[pos[0]:pos[0]+5] != 'false':
                raise Bad()
            pos[0] += 5
            return 'false'
        if c == '"':
            return esc(pstr())
        if c == '[':
            pos[0] += 1
            items = []
            skip_ws()
            if pos[0] < n and text[pos[0]] == ']':
                pos[0] += 1
                return '[]'
            while True:
                items.append(pval())
                skip_ws()
                if pos[0] >= n:
                    raise Bad()
                if text[pos[0]] == ',':
                    pos[0] += 1
                    continue
                if text[pos[0]] == ']':
                    pos[0] += 1
                    break
                raise Bad()
            return '[' + ','.join(items) + ']'
        if c == '{':
            pos[0] += 1
            pairs = []
            skip_ws()
            if pos[0] < n and text[pos[0]] == '}':
                pos[0] += 1
                return '{}'
            while True:
                skip_ws()
                if pos[0] >= n or text[pos[0]] != '"':
                    raise Bad()
                k = pstr()
                skip_ws()
                if pos[0] >= n or text[pos[0]] != ':':
                    raise Bad()
                pos[0] += 1
                v = pval()
                pairs.append((k, v))
                skip_ws()
                if pos[0] >= n:
                    raise Bad()
                if text[pos[0]] == ',':
                    pos[0] += 1
                    continue
                if text[pos[0]] == '}':
                    pos[0] += 1
                    break
                raise Bad()
            last = {}
            for k, v in pairs:
                last[k] = v
            keys = sorted(last.keys())
            return '{' + ','.join(esc(k) + ':' + last[k] for k in keys) + '}'
        if c == '-' or c.isdigit():
            st = pos[0]
            if text[pos[0]] == '-':
                pos[0] += 1
            if pos[0] >= n or not text[pos[0]].isdigit():
                raise Bad()
            if text[pos[0]] == '0':
                pos[0] += 1
            else:
                while pos[0] < n and text[pos[0]].isdigit():
                    pos[0] += 1
            return str(int(text[st:pos[0]]))
        raise Bad()

    try:
        r = pval()
        skip_ws()
        if pos[0] != n:
            return 'ERR'
    except Bad:
        return 'ERR'
    except (ValueError, IndexError, RecursionError):
        return 'ERR'
    return r
