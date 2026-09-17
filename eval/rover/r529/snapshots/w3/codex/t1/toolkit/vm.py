"""Subcommand module for `vm_run`: a tiny stack virtual machine."""

_STEP_LIMIT = 10000


def solve(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return "ERR"
    try:
        k = int(lines[0].strip())
    except ValueError:
        return "ERR"
    if not (1 <= k <= 64) or len(lines) < k + 1:
        return "ERR"
    prog = []
    for i in range(k):
        prog.append(_parse_instr(lines[i + 1]))
        if prog[-1] is None:
            return "ERR"
    stack = []
    pc = 0
    steps = 0
    out = []
    while True:
        if pc < 0 or pc >= k:
            return "ERR"
        if steps >= _STEP_LIMIT:
            return "ERR"
        steps += 1
        op = prog[pc]
        kind = op[0]
        nxt = pc + 1
        if kind == "PUSH":
            stack.append(op[1])
        elif kind == "POP":
            if not stack:
                return "ERR"
            stack.pop()
        elif kind in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if kind == "ADD":
                stack.append(b + a)
            elif kind == "SUB":
                stack.append(b - a)
            else:
                stack.append(b * a)
        elif kind == "DUP":
            if not stack:
                return "ERR"
            stack.append(stack[-1])
        elif kind == "SWAP":
            if len(stack) < 2:
                return "ERR"
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif kind == "PRINT":
            if not stack:
                return "ERR"
            out.append(str(stack.pop()))
        elif kind == "JNZ":
            if not stack:
                return "ERR"
            cond = stack.pop()
            if cond != 0:
                nxt = op[1]
        elif kind == "HALT":
            return "\n".join(out)
        pc = nxt


def _parse_instr(line):
    parts = line.split()
    if not parts:
        return None
    op = parts[0]
    if op == "PUSH" and len(parts) == 2:
        try:
            return ("PUSH", int(parts[1]))
        except ValueError:
            return None
    if op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT") and len(parts) == 1:
        return (op,)
    if op == "JNZ" and len(parts) == 2:
        try:
            return ("JNZ", int(parts[1]))
        except ValueError:
            return None
    return None
