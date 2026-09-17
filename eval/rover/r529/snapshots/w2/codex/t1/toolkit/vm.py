MAX_STEPS = 10000


def solve(text):
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return "ERR"
    head = lines[0].strip()
    if not head:
        return "ERR"
    try:
        k = int(head)
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    body = lines[1:]
    if len(body) != k:
        return "ERR"

    prog = []
    for raw in body:
        parsed = _parse_instr(raw)
        if parsed is None:
            return "ERR"
        prog.append(parsed)

    return _execute(prog)


def _execute(prog):
    k = len(prog)
    st = []
    out = []
    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > MAX_STEPS:
            return "ERR"
        if pc < 0 or pc >= k:
            return "ERR"
        op, arg = prog[pc]
        if op == "HALT":
            return "\n".join(out)
        pc += 1
        if op == "PUSH":
            st.append(arg)
        elif op == "POP":
            if not st:
                return "ERR"
            st.pop()
        elif op == "ADD":
            if len(st) < 2:
                return "ERR"
            a = st.pop()
            b = st.pop()
            st.append(b + a)
        elif op == "SUB":
            if len(st) < 2:
                return "ERR"
            a = st.pop()
            b = st.pop()
            st.append(b - a)
        elif op == "MUL":
            if len(st) < 2:
                return "ERR"
            a = st.pop()
            b = st.pop()
            st.append(b * a)
        elif op == "DUP":
            if not st:
                return "ERR"
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                return "ERR"
            st[-2], st[-1] = st[-1], st[-2]
        elif op == "PRINT":
            if not st:
                return "ERR"
            out.append(str(st.pop()))
        elif op == "JNZ":
            if not st:
                return "ERR"
            v = st.pop()
            if v != 0:
                if arg < 0 or arg >= k:
                    return "ERR"
                pc = arg


def _parse_instr(raw):
    parts = raw.strip().split()
    if not parts:
        return None
    op = parts[0]
    if op == "PUSH":
        if len(parts) != 2:
            return None
        try:
            return ("PUSH", int(parts[1]))
        except ValueError:
            return None
    if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
        if len(parts) != 1:
            return None
        return (op, None)
    if op == "JNZ":
        if len(parts) != 2:
            return None
        try:
            return ("JNZ", int(parts[1]))
        except ValueError:
            return None
    return None
