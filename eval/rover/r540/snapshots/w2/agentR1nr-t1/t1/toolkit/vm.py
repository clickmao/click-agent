"""vm stack machine: solve(text) -> str"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "ERR"
    head = lines[0].strip()
    if head == "":
        return "ERR"
    try:
        k = int(head)
    except ValueError:
        return "ERR"
    if not (1 <= k <= 64):
        return "ERR"
    prog = []
    for i in range(1, k + 1):
        if i >= len(lines):
            return "ERR"
        tok = lines[i].strip()
        if tok == "":
            return "ERR"
        parts = tok.split()
        if len(parts) > 2:
            return "ERR"
        prog.append(parts)
    out = []
    stack = []
    steps = 0
    pc = 0
    while True:
        steps += 1
        if steps > 10000:
            return "ERR\n".join(out + ["ERR"])
        if pc < 0 or pc >= len(prog):
            return "\n".join(out + ["ERR"])
        ins = prog[pc]
        op = ins[0]
        if op == "PUSH":
            if len(ins) != 2:
                return "\n".join(out + ["ERR"])
            try:
                n = int(ins[1])
            except ValueError:
                return "\n".join(out + ["ERR"])
            stack.append(n)
            pc += 1
        elif op == "POP":
            if not stack:
                return "\n".join(out + ["ERR"])
            stack.pop()
            pc += 1
        elif op == "ADD":
            if len(stack) < 2:
                return "\n".join(out + ["ERR"])
            a = stack.pop()
            b = stack.pop()
            stack.append(b + a)
            pc += 1
        elif op == "SUB":
            if len(stack) < 2:
                return "\n".join(out + ["ERR"])
            a = stack.pop()
            b = stack.pop()
            stack.append(b - a)
            pc += 1
        elif op == "MUL":
            if len(stack) < 2:
                return "\n".join(out + ["ERR"])
            a = stack.pop()
            b = stack.pop()
            stack.append(b * a)
            pc += 1
        elif op == "DUP":
            if not stack:
                return "\n".join(out + ["ERR"])
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return "\n".join(out + ["ERR"])
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return "\n".join(out + ["ERR"])
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if len(ins) != 2:
                return "\n".join(out + ["ERR"])
            if not stack:
                return "\n".join(out + ["ERR"])
            try:
                a = int(ins[1])
            except ValueError:
                return "\n".join(out + ["ERR"])
            v = stack.pop()
            if v != 0:
                if a < 0 or a >= len(prog):
                    return "\n".join(out + ["ERR"])
                pc = a
            else:
                pc += 1
        elif op == "HALT":
            if len(ins) != 1:
                return "\n".join(out + ["ERR"])
            return "\n".join(out)
        else:
            return "\n".join(out + ["ERR"])
