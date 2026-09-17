def solve(text: str) -> str:
    n = len(text)
    pos = 0

    def skip_ws():
        nonlocal pos
        while pos < n and text[pos] in " \t\n\r":
            pos += 1

    def parse_value():
        nonlocal pos
        skip_ws()
        if pos >= n:
            raise ValueError("eof")
        c = text[pos]
        if c == "{":
            return parse_object()
        if c == "[":
            return parse_array()
        if c == '"':
            return parse_string()
        if c == "t":
            if text[pos:pos + 4] == "true":
                pos += 4
                return ("true", True)
            raise ValueError("bad")
        if c == "f":
            if text[pos:pos + 5] == "false":
                pos += 5
                return ("false", False)
            raise ValueError("bad")
        if c == "n":
            if text[pos:pos + 4] == "null":
                pos += 4
                return ("null", None)
            raise ValueError("bad")
        if c == "-" or c.isdigit():
            return parse_number()
        raise ValueError("bad")

    def parse_number():
        nonlocal pos
        start = pos
        if pos < n and text[pos] == "-":
            pos += 1
        if pos >= n or not text[pos].isdigit():
            raise ValueError("bad")
        if text[pos] == "0":
            pos += 1
            if pos < n and text[pos].isdigit():
                raise ValueError("bad")
        else:
            while pos < n and text[pos].isdigit():
                pos += 1
        return ("num", int(text[start:pos]))

    def parse_string():
        nonlocal pos
        if text[pos] != '"':
            raise ValueError("bad")
        pos += 1
        out = []
        while True:
            if pos >= n:
                raise ValueError("bad")
            c = text[pos]
            if c == '"':
                pos += 1
                break
            if c == "\\":
                pos += 1
                if pos >= n:
                    raise ValueError("bad")
                e = text[pos]
                if e == "u":
                    if pos + 4 >= n:
                        raise ValueError("bad")
                    hexs = text[pos + 1:pos + 5]
                    for ch in hexs:
                        if ch not in "0123456789abcdefABCDEF":
                            raise ValueError("bad")
                    cp = int(hexs, 16)
                    if cp < 0x20:
                        raise ValueError("bad")
                    out.append(chr(cp))
                    pos += 5
                elif e == '"':
                    out.append('"')
                    pos += 1
                elif e == "\\":
                    out.append("\\")
                    pos += 1
                elif e == "/":
                    out.append("/")
                    pos += 1
                elif e == "n":
                    out.append("\n")
                    pos += 1
                elif e == "t":
                    out.append("\t")
                    pos += 1
                else:
                    raise ValueError("bad")
            else:
                if ord(c) < 0x20:
                    raise ValueError("bad")
                out.append(c)
                pos += 1
        return ("str", "".join(out))

    def parse_array():
        nonlocal pos
        pos += 1
        items = []
        skip_ws()
        if pos < n and text[pos] == "]":
            pos += 1
            return ("arr", items)
        while True:
            items.append(parse_value())
            skip_ws()
            if pos >= n:
                raise ValueError("bad")
            if text[pos] == ",":
                pos += 1
                continue
            if text[pos] == "]":
                pos += 1
                break
            raise ValueError("bad")
        return ("arr", items)

    def parse_object():
        nonlocal pos
        pos += 1
        items = []
        seen = {}
        order = []
        skip_ws()
        if pos < n and text[pos] == "}":
            pos += 1
            return ("obj", order, seen)
        while True:
            skip_ws()
            key = parse_string()[1]
            skip_ws()
            if pos >= n or text[pos] != ":":
                raise ValueError("bad")
            pos += 1
            val = parse_value()
            if key not in seen:
                order.append(key)
            seen[key] = val
            skip_ws()
            if pos >= n:
                raise ValueError("bad")
            if text[pos] == ",":
                pos += 1
                continue
            if text[pos] == "}":
                pos += 1
                break
            raise ValueError("bad")
        return ("obj", order, seen)

    def escape(s):
        out = []
        for ch in s:
            if ch == '"':
                out.append('\\"')
            elif ch == "\\":
                out.append("\\\\")
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        return '"' + "".join(out) + '"'

    def render(node):
        tag = node[0]
        if tag == "num":
            return str(node[1])
        if tag == "true":
            return "true"
        if tag == "false":
            return "false"
        if tag == "null":
            return "null"
        if tag == "str":
            return escape(node[1])
        if tag == "arr":
            return "[" + ",".join(render(x) for x in node[1]) + "]"
        if tag == "obj":
            keys = sorted(node[1])
            parts = []
            for kk in keys:
                parts.append(escape(kk) + ":" + render(node[2][kk]))
            return "{" + ",".join(parts) + "}"
        raise ValueError("bad")

    try:
        node = parse_value()
        skip_ws()
        if pos != n:
            return "ERR"
        return render(node)
    except Exception:
        return "ERR"
