"""VM subcommand: parse and execute a tiny stack machine."""

MAX_STEPS = 10000


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"

    program = []
    for i in range(1, k + 1):
        if i >= len(lines):
            return "ERR"
        program.append(lines[i].strip())

    stack = []
    out = []
    pc = 0
    steps = 0

    while True:
        if pc < 0 or pc >= k:
            return "ERR"
        if steps >= MAX_STEPS:
            return "ERR"
        steps += 1
        instr = program[pc]
        parts = instr.split()
        op = parts[0] if parts else ""

        if op == "HALT":
            return "\n".join(out)
        elif op == "PUSH":
            if len(parts) != 2:
                return "ERR"
            try:
                stack.append(int(parts[1]))
            except ValueError:
                return "ERR"
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
            if len(parts) != 2 or not stack:
                return "ERR"
            try:
                target = int(parts[1])
            except ValueError:
                return "ERR"
            v = stack.pop()
            if target < 0 or target >= k:
                return "ERR"
            if v != 0:
                pc = target
            else:
                pc += 1
        else:
            return "ERR"
