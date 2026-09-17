"""vm_run subcommand: a tiny stack VM interpreter.

solve(text) -> str: stdin text in, stdout text out (no trailing newline).
"""

ERR = "ERR"


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ERR
    try:
        k = int(lines[0].strip())
    except ValueError:
        return ERR
    if k < 1 or k > 64:
        return ERR
    if len(lines) - 1 < k:
        return ERR
    prog = []
    for i in range(1, k + 1):
        raw = lines[i].strip()
        if raw == "":
            return ERR
        parts = raw.split()
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return ERR
            try:
                n = int(parts[1])
            except ValueError:
                return ERR
            prog.append((op, n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return ERR
            prog.append((op, None))
        elif op == "JNZ":
            if len(parts) != 2:
                return ERR
            try:
                a = int(parts[1])
            except ValueError:
                return ERR
            prog.append((op, a))
        else:
            return ERR

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if pc < 0 or pc >= k:
            return ERR
        if steps >= 10000:
            return ERR
        steps += 1
        op, arg = prog[pc]
        if op == "HALT":
            break
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                return ERR
            stack.pop()
            pc += 1
        elif op == "ADD":
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            pc += 1
        elif op == "SUB":
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            pc += 1
        elif op == "MUL":
            if len(stack) < 2:
                return ERR
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if not stack:
                return ERR
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return ERR
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return ERR
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return ERR
            v = stack.pop()
            if v != 0:
                if arg < 0 or arg >= k:
                    return ERR
                pc = arg
            else:
                pc += 1
        else:
            return ERR
    return "\n".join(out)
