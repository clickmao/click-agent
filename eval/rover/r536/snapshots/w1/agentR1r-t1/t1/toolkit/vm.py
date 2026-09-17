"""vm_run: stack VM interpreter."""


def solve(text: str) -> str:
    lines = text.split("\n")
    try:
        k = int(lines[0].strip())
    except Exception:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"
    if len(lines) < k + 1:
        return "ERR"
    prog = [ln for ln in lines[1:1 + k]]
    prog = [ln.strip() for ln in prog]

    stack = []
    out = []

    def pop():
        if not stack:
            raise ValueError
        return stack.pop()

    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if pc < 0 or pc >= len(prog):
            return "ERR"
        ins = prog[pc]
        op, _, arg = ins.partition(" ")
        try:
            if op == "PUSH":
                stack.append(int(arg.strip()))
            elif op == "POP":
                pop()
            elif op == "ADD":
                a = pop()
                b = pop()
                stack.append(b + a)
            elif op == "SUB":
                a = pop()
                b = pop()
                stack.append(b - a)
            elif op == "MUL":
                a = pop()
                b = pop()
                stack.append(b * a)
            elif op == "DUP":
                if not stack:
                    raise ValueError
                stack.append(stack[-1])
            elif op == "SWAP":
                if len(stack) < 2:
                    raise ValueError
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "PRINT":
                out.append(str(pop()))
            elif op == "JNZ":
                v = pop()
                if v != 0:
                    pc = int(arg.strip())
                    continue
            elif op == "HALT":
                break
            else:
                return "ERR"
        except Exception:
            return "ERR"
        pc += 1
    return "\n".join(out)
