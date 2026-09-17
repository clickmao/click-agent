def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) < 1 + k:
        return "ERR"
    prog = []
    for i in range(k):
        prog.append(lines[1 + i].strip())

    stack = []
    out = []
    ip = 0
    steps = 0
    pc = len(prog)

    def need(n):
        return len(stack) >= n

    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if ip < 0 or ip >= pc:
            return "ERR"
        parts = prog[ip].split()
        op = parts[0]
        arg = parts[1] if len(parts) > 1 else None
        if arg is not None and len(parts) != 2:
            return "ERR"

        if op == "PUSH":
            if arg is None:
                return "ERR"
            try:
                v = int(arg)
            except ValueError:
                return "ERR"
            stack.append(v)
            ip += 1
        elif op == "POP":
            if not need(1):
                return "ERR"
            stack.pop()
            ip += 1
        elif op in ("ADD", "SUB", "MUL"):
            if not need(2):
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
            ip += 1
        elif op == "DUP":
            if not need(1):
                return "ERR"
            stack.append(stack[-1])
            ip += 1
        elif op == "SWAP":
            if not need(2):
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            stack.append(a)
            stack.append(b)
            ip += 1
        elif op == "PRINT":
            if not need(1):
                return "ERR"
            out.append(str(stack.pop()))
            ip += 1
        elif op == "JNZ":
            if arg is None:
                return "ERR"
            try:
                t = int(arg)
            except ValueError:
                return "ERR"
            if not need(1):
                return "ERR"
            v = stack.pop()
            if v != 0:
                if t < 0 or t >= pc:
                    return "ERR"
                ip = t
            else:
                ip += 1
        elif op == "HALT":
            return "\n".join(out)
        else:
            return "ERR"
