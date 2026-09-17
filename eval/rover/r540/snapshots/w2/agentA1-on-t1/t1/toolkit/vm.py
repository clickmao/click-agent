"""vm_run: stack virtual machine interpreter.

stdin: first line integer k (1<=k<=64), then k lines of instructions.
Output: values from PRINT, one per line. On any error: single line "ERR".
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    if not lines:
        return "ERR"
    head = lines[0].strip()
    if not head or not head.lstrip("+-").isdigit():
        return "ERR"
    try:
        k = int(head)
    except ValueError:
        return "ERR"
    if k < 1 or k > 64:
        return "ERR"

    prog = []
    for i in range(k):
        if i + 1 >= len(lines):
            return "ERR"
        raw = lines[i + 1].strip()
        parts = raw.split()
        if not parts:
            return "ERR"
        op = parts[0]
        if op in ("PUSH",):
            if len(parts) != 2 or not _is_int(parts[1]):
                return "ERR"
            prog.append((op, int(parts[1])))
        elif op in ("POP", "ADD", "SUB", "MUL", "DUP", "SWAP", "PRINT", "HALT"):
            if len(parts) != 1:
                return "ERR"
            prog.append((op, None))
        elif op == "JNZ":
            if len(parts) != 2 or not _is_int(parts[1]):
                return "ERR"
            prog.append((op, int(parts[1])))
        else:
            return "ERR"

    stack = []
    out = []
    pc = 0
    steps = 0
    while True:
        steps += 1
        if steps > 10000:
            return "ERR"
        if pc < 0 or pc >= k:
            return "ERR"
        op, arg = prog[pc]
        if op == "PUSH":
            stack.append(arg)
            pc += 1
        elif op == "POP":
            if not stack:
                return "ERR"
            stack.pop()
            pc += 1
        elif op in ("ADD", "SUB", "MUL"):
            if len(stack) < 2:
                return "ERR"
            a = stack.pop()
            b = stack.pop()
            if op == "ADD":
                stack.append(b + a)
            elif op == "SUB":
                stack.append(b - a)
            else:
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
                if arg < 0 or arg >= k:
                    return "ERR"
                pc = arg
            else:
                pc += 1
        elif op == "HALT":
            return "\n".join(out)
        else:
            return "ERR"


def _is_int(s: str) -> bool:
    if not s:
        return False
    body = s[1:] if s[0] in "+-" else s
    return body.isdigit() and body.isascii()
