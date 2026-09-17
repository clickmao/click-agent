def solve(text: str) -> str:
    tokens = text.split()
    if not tokens:
        return "ERR"
    try:
        k = int(tokens[0])
    except ValueError:
        return "ERR"
    if not (1 <= k <= 64):
        return "ERR"
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    prog = []
    for ln in lines[1:]:
        parts = ln.split()
        prog.append(parts)
    if len(prog) < k:
        return "ERR"
    prog = prog[:k]
    stack = []
    out = []
    steps = 0
    pc = 0
    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if pc < 0 or pc >= len(prog):
            return "ERR"
        inst = prog[pc]
        op = inst[0]
        try:
            if op == "PUSH":
                stack.append(int(inst[1]))
            elif op == "POP":
                stack.pop()
            elif op == "ADD":
                a = stack.pop(); b = stack.pop(); stack.append(b + a)
            elif op == "SUB":
                a = stack.pop(); b = stack.pop(); stack.append(b - a)
            elif op == "MUL":
                a = stack.pop(); b = stack.pop(); stack.append(b * a)
            elif op == "DUP":
                stack.append(stack[-1])
            elif op == "SWAP":
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "PRINT":
                out.append(str(stack.pop()))
            elif op == "JNZ":
                v = stack.pop()
                if v != 0:
                    pc = int(inst[1])
                    continue
            elif op == "HALT":
                break
            else:
                return "ERR"
        except (IndexError, ValueError):
            return "ERR"
        pc += 1
    return "\n".join(out)
