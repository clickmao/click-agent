"""vm_run: tiny stack VM interpreter.

stdin format:
    line 0: integer k (1<=k<=64, instruction count)
    next k lines: one instruction each (addresses start at 0)

instruction set:
    PUSH n / POP / ADD / SUB / MUL / DUP / SWAP / PRINT / JNZ a / HALT

binary ops: pop a = top, b = next, push b <op> a
    ADD -> b + a, SUB -> b - a, MUL -> b * a

output: one line per PRINT, in order.
error (stack underflow, bad jump target, step budget exceeded,
control flow past last instruction, malformed input): single line "ERR".
"""

MAX_STEPS = 10000


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
    program = []
    for i in range(k):
        program.append(lines[1 + i].strip())

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        if steps >= MAX_STEPS:
            return "ERR"
        steps += 1
        if pc < 0 or pc >= k:
            return "ERR"
        parts = program[pc].split()
        if not parts:
            return "ERR"
        op = parts[0]
        pc += 1
        if op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                v = int(parts[1])
            except ValueError:
                return "ERR"
            stack.append(v)
        elif op == "POP":
            if len(parts) != 1 or not stack:
                return "ERR"
            stack.pop()
        elif op in ("ADD", "SUB", "MUL"):
            if len(parts) != 1 or len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
        elif op == "DUP":
            if len(parts) != 1 or not stack:
                return "ERR"
            stack.append(stack[-1])
        elif op == "SWAP":
            if len(parts) != 1 or len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == "PRINT":
            if len(parts) != 1 or not stack:
                return "ERR"
            out.append(str(stack.pop()))
        elif op == "JNZ":
            if len(parts) != 2 or not stack:
                return "ERR"
            try:
                a = int(parts[1])
            except ValueError:
                return "ERR"
            v = stack.pop()
            if v != 0:
                if a < 0 or a >= k:
                    return "ERR"
                pc = a
        elif op == "HALT":
            if len(parts) != 1:
                return "ERR"
            return "\n".join(out)
        else:
            return "ERR"
