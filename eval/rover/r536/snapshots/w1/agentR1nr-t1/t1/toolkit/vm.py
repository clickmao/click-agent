def solve(text: str) -> str:
    lines = text.split("\n")
    idx = 0
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return "ERR"
    try:
        k = int(lines[idx].strip())
    except Exception:
        return "ERR"
    idx += 1
    prog = []
    for _ in range(k):
        if idx >= len(lines):
            return "ERR"
        raw = lines[idx].strip()
        idx += 1
        parts = raw.split()
        if not parts:
            return "ERR"
        op = parts[0]
        if op in ("PUSH", "JNZ"):
            if len(parts) != 2:
                return "ERR"
            try:
                arg = int(parts[1])
            except Exception:
                return "ERR"
            prog.append((op, arg))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            prog.append((op, None))
        else:
            return "ERR"
    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= len(prog):
            return "ERR"
        steps += 1
        if steps > 10000:
            return "ERR"
        op, arg = prog[pc]
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op == "ADD":
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            pc += 1
        elif op == "SUB":
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            pc += 1
        elif op == "MUL":
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if not stack:
                return "ERR"
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return "ERR"
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return "ERR"
            v = stack.pop()
            if v != 0:
                if arg < 0 or arg >= len(prog):
                    return "ERR"
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            break
    return "\n".join(out)
