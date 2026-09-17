"""vm 子命令: 栈式虚拟机解释器.

solve(text) -> str: 入参为完整 stdin 文本, 返回应写出的 stdout 文本(末尾不带换行).
"""

MAX_STEPS = 10000


def solve(text: str) -> str:
    lines = text.split("\n")
    # 首行 = 指令条数 k
    if not lines:
        return "ERR"
    head = lines[0].strip()
    try:
        k = int(head)
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"

    # 取随后 k 行作为指令; 行数不足则非法
    if len(lines) < 1 + k:
        return "ERR"
    prog_lines = [lines[1 + i] for i in range(k)]

    prog = []
    for ln in prog_lines:
        parts = ln.strip().split()
        if not parts:
            return "ERR"
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                n = int(parts[1])
            except ValueError:
                return "ERR"
            prog.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            prog.append((op,))
        elif op == "JNZ":
            if len(parts) != 2:
                return "ERR"
            try:
                a = int(parts[1])
            except ValueError:
                return "ERR"
            prog.append(("JNZ", a))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0

    def fail():
        return "ERR"

    while True:
        if pc < 0 or pc >= len(prog):
            return fail()
        if steps >= MAX_STEPS:
            return fail()
        steps += 1
        ins = prog[pc]
        op = ins[0]

        if op == "PUSH":
            stack.append(ins[1])
            pc += 1
        elif op == "POP":
            if not stack:
                return fail()
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return fail()
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
        elif op == "DUP":
            if not stack:
                return fail()
            stack.append(stack[-1])
            pc += 1
        elif op == "SWAP":
            if len(stack) < 2:
                return fail()
            stack[-1], stack[-2] = stack[-2], stack[-1]
            pc += 1
        elif op == "PRINT":
            if not stack:
                return fail()
            out.append(str(stack.pop()))
            pc += 1
        elif op == "JNZ":
            if not stack:
                return fail()
            v = stack.pop()
            target = ins[1]
            if v != 0:
                if target < 0 or target >= len(prog):
                    return fail()
                pc = target
            else:
                pc += 1
        elif op == "HALT":
            return "\n".join(out)
        else:
            return fail()
