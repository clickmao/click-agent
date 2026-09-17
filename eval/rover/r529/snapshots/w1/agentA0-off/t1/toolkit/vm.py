"""vm: stack machine interpreter.

Instruction set (addresses start at 0):
    PUSH n   push integer n
    POP      pop and discard top
    ADD/SUB/MUL   pop a=top, b=next, push b-a / b-a / b*a
    DUP      duplicate top
    SWAP     swap top two elements
    PRINT    pop top and emit one line
    JNZ a    pop top; if nonzero jump to address a
    HALT     stop

Output: values printed by PRINT, one per line.
Any error (pop on empty stack, insufficient operands, out-of-range jump,
no HALT within 10000 steps, or control flow past the last instruction)
yields a single line "ERR".
"""


class _Err(Exception):
    pass


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "ERR"
    head = lines[0].strip()
    try:
        k = int(head)
    except ValueError:
        return "ERR"
    if not (1 <= k <= 64):
        return "ERR"
    prog = lines[1:1 + k]
    if len(prog) < k:
        return "ERR"

    code = []
    for raw in prog:
        parts = raw.strip().split()
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
            code.append(("PUSH", n))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            code.append((op, None))
        elif op == "JNZ":
            if len(parts) != 2:
                return "ERR"
            try:
                a = int(parts[1])
            except ValueError:
                return "ERR"
            code.append(("JNZ", a))
        else:
            return "ERR"

    pc = 0
    stack = []
    out = []
    steps = 0
    n = len(code)
    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if pc < 0 or pc >= n:
            return "ERR"
        op, arg = code[pc]
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
                if arg < 0 or arg >= n:
                    return "ERR"
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            return "\n".join(out)
        else:
            return "ERR"
