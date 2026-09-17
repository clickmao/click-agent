"""vm_run: 栈式虚拟机解释器。solve(text) -> str (stdout 文本, 末尾不带换行)。"""

_OPS0 = ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT")


def solve(text: str) -> str:
    lines = text.split("\n")
    try:
        k = int(lines[0].strip())
    except (IndexError, ValueError):
        return "ERR"
    if not (1 <= k <= 64):
        return "ERR"
    if len(lines) < 1 + k:
        return "ERR"
    prog = []
    for i in range(1, 1 + k):
        toks = lines[i].split()
        if not toks:
            return "ERR"
        op = toks[0]
        if op == "PUSH":
            if len(toks) != 2:
                return "ERR"
            try:
                n = int(toks[1])
            except ValueError:
                return "ERR"
            prog.append(("PUSH", n))
        elif op in _OPS0:
            if len(toks) != 1:
                return "ERR"
            prog.append((op,))
        elif op == "JNZ":
            if len(toks) != 2:
                return "ERR"
            try:
                a = int(toks[1])
            except ValueError:
                return "ERR"
            prog.append(("JNZ", a))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if steps >= 10000:
            return "ERR"
        if pc < 0 or pc >= k:
            return "ERR"
        steps += 1
        ins = prog[pc]
        op = ins[0]
        if op == "PUSH":
            stack.append(ins[1])
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
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
        elif op == "ADD" or op == "SUB" or op == "MUL":
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                r = b + a
            elif op == "SUB":
                r = b - a
            else:
                r = b * a
            stack.append(r)
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
                pc = ins[1]
            else:
                pc += 1
        else:  # HALT
            return "\n".join(out)
